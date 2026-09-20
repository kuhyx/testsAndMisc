#!/usr/bin/env python3
"""Prove Helium ships full uBlock Origin (MV2) and honours the Chromium policies.

Runs Helium under a private Xvfb display (never the live desktop) and asserts by
exit code: uBO has a ``background_page`` and ``manifest_version: 2`` (full, not
Lite); every ``/etc/chromium/policies/managed`` key shows on ``chrome://policy``;
adblock-tester.com scores >= ``MIN_SCORE``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Self

from websockets.sync.client import connect

HELIUM_BIN = "/usr/bin/helium-browser"
HELIUM_BIN_DIR = "/opt/helium-browser-bin"
DEFAULT_PROFILE = str(Path.home() / ".config" / "net.imput.helium")
UBO_ID = "blockjmkbacgjkknlgpkjjiijinjdanf"
POLICY_DIR = Path("/etc/chromium/policies/managed")
ADBLOCK_TEST_URL = "https://adblock-tester.com/"
MIN_SCORE = 95
HTTP_OK = 200
DISPLAY = f":{100 + os.getpid() % 900}"  # private Xvfb, unique per run
# Walks light DOM and every open shadow root — chrome://policy is Polymer.
DEEP_TEXT_JS = (
    "(() => { const o = []; const w = (n) => { if (n.shadowRoot) w(n.shadowRoot);"
    " for (const c of n.childNodes) { if (c.nodeType === 3) o.push(c.textContent);"
    " else w(c); } }; w(document); return o.join(' '); })()"
)
Proc = subprocess.Popen[bytes]
Json = list[dict[str, str]] | dict[str, str]


@dataclass(frozen=True)
class Check:
    """One named pass/fail result with the evidence behind it."""

    name: str
    ok: bool
    detail: str


def say(msg: str, *, err: bool = False) -> None:
    """Write one line; explicit stream write so lint autofix cannot drop it."""
    (sys.stderr if err else sys.stdout).write(msg + "\n")


def devtools_json(port: int, method: str, path: str) -> Json:
    """One request against Helium's DevTools HTTP endpoint on loopback."""
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path)
        resp = conn.getresponse()
        if resp.status != HTTP_OK:
            msg = f"{method} {path} -> HTTP {resp.status}"
            raise OSError(msg)
        return json.loads(resp.read())
    finally:
        conn.close()


def wait_for_devtools(profile: str, timeout: float = 30.0) -> int:
    """Wait for Chromium to publish its chosen port in <profile>/DevToolsActivePort."""
    port_file = Path(profile) / "DevToolsActivePort"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            port = int(port_file.read_text().splitlines()[0])
            devtools_json(port, "GET", "/json/list")
        except OSError, ValueError, IndexError:
            time.sleep(0.5)
        else:
            return port
    msg = "DevTools never came up"
    raise TimeoutError(msg)


class Page:
    """Minimal CDP client bound to one fresh tab; use as a context manager."""

    def __init__(self, port: int, url: str, settle: float) -> None:
        """Open a tab at ``url``, attach, and give it ``settle`` seconds to render."""
        target = devtools_json(port, "PUT", f"/json/new?{url}")
        self._ws = connect(target["webSocketDebuggerUrl"], max_size=None)
        self._next_id = 0
        time.sleep(settle)

    def __enter__(self) -> Self:
        """Context-manager entry."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the CDP socket."""
        self._ws.close()

    def evaluate(self, expression: str) -> str:
        """Run JS in the page and return its string result."""
        self._next_id += 1
        params = {"expression": expression, "returnByValue": True}
        msg = {"id": self._next_id, "method": "Runtime.evaluate", "params": params}
        self._ws.send(json.dumps(msg))
        while True:
            msg = json.loads(self._ws.recv(timeout=30))
            if msg.get("id") == self._next_id:
                return str(msg.get("result", {}).get("result", {}).get("value", ""))

    def text(self) -> str:
        """Visible text of the page's light DOM."""
        return self.evaluate("document.body.innerText")


def check_ubo_mv2(port: int, targets: list[dict[str, str]]) -> Check:
    """UBO full runs a persistent background page; uBO Lite/MV3 cannot."""
    ubo = [t for t in targets if UBO_ID in t.get("url", "")]
    has_bg_page = any(t.get("type") == "background_page" for t in ubo)
    with Page(port, f"chrome-extension://{UBO_ID}/manifest.json", 1.5) as page:
        manifest = page.text()
    mv = re.search(r'"manifest_version"\s*:\s*(\d)', manifest)
    name = re.search(r'"name"\s*:\s*"([^"]+)"', manifest)
    version = re.search(r'"version"\s*:\s*"([^"]+)"', manifest)
    ok = has_bg_page and mv is not None and mv.group(1) == "2"
    detail = (
        f"name={name.group(1) if name else '?'}"
        f" version={version.group(1) if version else '?'}"
        f" manifest_version={mv.group(1) if mv else '?'} background_page={has_bg_page}"
    )
    return Check("uBlock Origin is MV2 (full, not Lite)", ok, detail)


def check_policies(port: int) -> Check:
    """Every key in every managed policy JSON must be listed on chrome://policy."""
    expected: set[str] = set()
    for f in sorted(POLICY_DIR.glob("*.json")):
        expected.update(json.loads(f.read_text()).keys())
    with Page(port, "chrome://policy", 2.0) as page:
        text = page.evaluate(DEEP_TEXT_JS)
    missing = sorted(k for k in expected if k not in text)
    return Check(
        f"{len(expected)} policies from {POLICY_DIR} applied",
        not missing,
        f"missing={missing}" if missing else f"all present: {sorted(expected)}",
    )


def check_adblock_score(port: int) -> Check:
    """adblock-tester.com prints "<N> points out of 100" once its probes finish."""
    score = -1
    with Page(port, ADBLOCK_TEST_URL, 0.5) as page:
        for _ in range(40):  # up to ~20 s for the probes to finish
            m = re.search(r"(\d{1,3}) points out of 100", page.text())
            if m:
                score = int(m.group(1))
                break
            time.sleep(0.5)
    name = f"adblock-tester score >= {MIN_SCORE}/100"
    return Check(name, score >= MIN_SCORE, f"score={score}")


def launch(profile: str) -> tuple[Proc, Proc]:
    """Start Xvfb and Helium; caller must stop both."""
    (Path(profile) / "DevToolsActivePort").unlink(missing_ok=True)
    xvfb_cmd = ["/usr/bin/Xvfb", DISPLAY, "-screen", "0", "1280x800x24"]
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    xvfb = subprocess.Popen(xvfb_cmd, **quiet)
    time.sleep(1.0)
    flags = ["--no-first-run", "--disable-gpu", "--remote-allow-origins=*"]
    flags += ["--remote-debugging-port=0", f"--user-data-dir={profile}"]
    env = {"DISPLAY": DISPLAY, "HOME": str(Path.home()), "PATH": "/usr/bin"}
    helium = subprocess.Popen([HELIUM_BIN, *flags, "about:blank"], env=env, **quiet)
    return xvfb, helium


def helium_running() -> bool:
    """True if any Helium process is alive."""
    cmd = ["/usr/bin/pgrep", "-f", HELIUM_BIN_DIR]
    return subprocess.run(cmd, check=False, capture_output=True).returncode == 0


def stop(proc: Proc) -> None:
    """SIGTERM then SIGKILL after a grace period."""
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def parse_args() -> argparse.Namespace:
    """CLI flags."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--user-data-dir",
        default=DEFAULT_PROFILE,
        help="profile to test (default: the real Helium profile)",
    )
    return parser.parse_args()


def main() -> int:
    """Run all checks; exit 1 if any fails."""
    args = parse_args()
    if not Path(HELIUM_BIN).exists() or shutil.which("Xvfb") is None:
        say(f"need {HELIUM_BIN} and Xvfb", err=True)
        return 2
    # A second instance on an open profile hands off to the running one and
    # exits, so DevTools would never appear.
    if args.user_data_dir == DEFAULT_PROFILE and helium_running():
        say(
            "Helium is already running — close it first (or pass --user-data-dir).",
            err=True,
        )
        return 3
    xvfb, helium = launch(args.user_data_dir)
    try:
        port = wait_for_devtools(args.user_data_dir)
        time.sleep(3.0)  # let component extensions finish loading
        targets = devtools_json(port, "GET", "/json/list")
        checks = (check_ubo_mv2(port, targets), check_policies(port))
        results = [*checks, check_adblock_score(port)]
    finally:
        stop(helium)
        stop(xvfb)
    for r in results:
        say(f"[{'PASS' if r.ok else 'FAIL'}] {r.name}: {r.detail}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
