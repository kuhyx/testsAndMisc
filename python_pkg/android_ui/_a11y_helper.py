"""Accessibility-tree dumps of any display, via a tiny instrumentation APK.

``uiautomator dump`` only ever sees display 0, so an app on a session's
virtual display (``phone_vd.sh``) could only be tapped by coordinates. The
APK built from ``A11yDump.java`` runs under ``am instrument``, where a UiAutomation can
read ``getWindowsOnAllDisplays()`` and print one display's tree in the same
XML shape ``uiautomator`` writes.

It is built from source here (javac → d8 → aapt2 → apksigner, no Gradle),
cached by source hash under ``~/.cache/android_ui/``, and (re)installed with
``adb install -r -t`` whenever the phone holds a different build. The APK is
never committed: the repo's binary gate forbids it, and the source is enough.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from python_pkg.android_ui._elements import UiAutomationError

PACKAGE = "com.kuhy.a11ydump"
_RUNNER = f"{PACKAGE}/.A11yDump"
# Flat beside this module: the repo caps paths at two directories, and javac
# does not need the package's directory layout for an explicitly named file.
_JAVA = Path(__file__).with_name("A11yDump.java")
_MANIFEST = Path(__file__).with_name("a11y_dump_manifest.xml")
_MIN_API = "30"  # getWindowsOnAllDisplays()

# (adb args...) -> stdout, raising UiAutomationError on failure.
AdbRun = Callable[..., str]


def source_hash() -> str:
    """Hash of every source file: the build's identity and versionName."""
    digest = hashlib.sha256()
    for path in (_JAVA, _MANIFEST):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def cache_dir() -> Path:
    """Where built APKs are kept."""
    return Path(
        os.environ.get("ANDROID_UI_CACHE", Path.home() / ".cache" / "android_ui")
    )


def sdk_root() -> Path:
    """The Android SDK, from $ANDROID_HOME / $ANDROID_SDK_ROOT."""
    for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(var)
        if value and Path(value).is_dir():
            return Path(value)
    fallback = Path.home() / "sdk" / "Android" / "Sdk"
    if fallback.is_dir():
        return fallback
    msg = "no Android SDK: set ANDROID_HOME (needs build-tools and a platform)"
    raise UiAutomationError(msg)


def _newest(parent: Path, prefix: str = "") -> Path:
    candidates = sorted(
        (p for p in parent.iterdir() if p.name.startswith(prefix) and p.is_dir()),
        key=lambda p: [
            int(x) if x.isdigit() else 0 for x in p.name.split("-")[-1].split(".")
        ],
    )
    if not candidates:
        msg = f"nothing matching {prefix!r} under {parent}"
        raise UiAutomationError(msg)
    return candidates[-1]


def build_tool(name: str) -> Path:
    """Absolute path of an SDK build tool (``aapt2``, ``d8``, ...), newest version."""
    return _newest(sdk_root() / "build-tools") / name


def _tool(*cmd: str | Path) -> None:
    done = subprocess.run(
        [str(c) for c in cmd], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        msg = f"building the a11y helper failed: {cmd[0]}\n{done.stderr.strip()}"
        raise UiAutomationError(msg)


def build() -> Path:
    """Return the helper APK for the current source, building it if needed."""
    version = source_hash()
    apk = cache_dir() / f"a11ydump-{version}.apk"
    if apk.is_file():
        return apk
    sdk = sdk_root()
    tools = _newest(sdk / "build-tools")
    android_jar = _newest(sdk / "platforms", "android-") / "android.jar"
    keystore = Path.home() / ".android" / "debug.keystore"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        classes, dex = work / "classes", work / "dex"
        classes.mkdir()
        dex.mkdir()
        _tool(
            "javac",
            "--release",
            "11",
            "-classpath",
            android_jar,
            "-d",
            classes,
            _JAVA,
        )
        class_files = sorted(str(p) for p in classes.rglob("*.class"))
        _tool(
            tools / "d8",
            "--release",
            "--min-api",
            _MIN_API,
            "--lib",
            android_jar,
            "--output",
            dex,
            *class_files,
        )
        unsigned = work / "unsigned.apk"
        _tool(
            tools / "aapt2",
            "link",
            "--manifest",
            _MANIFEST,
            "-I",
            android_jar,
            "--version-code",
            "1",
            "--version-name",
            version,
            "-o",
            unsigned,
        )
        with zipfile.ZipFile(unsigned, "a") as zf:
            zf.write(dex / "classes.dex", "classes.dex")
        aligned = work / "aligned.apk"
        _tool(tools / "zipalign", "-f", "4", unsigned, aligned)
        if not keystore.is_file():
            _tool(
                "keytool",
                "-genkeypair",
                "-keystore",
                keystore,
                "-storepass",
                "android",
                "-alias",
                "androiddebugkey",
                "-keypass",
                "android",
                "-keyalg",
                "RSA",
                "-validity",
                "10000",
                "-dname",
                "CN=Android Debug,O=Android,C=US",
            )
        _tool(
            tools / "apksigner",
            "sign",
            "--ks",
            keystore,
            "--ks-pass",
            "pass:android",
            "--key-pass",
            "pass:android",
            "--out",
            work / "signed.apk",
            aligned,
        )
        apk.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(work / "signed.apk", apk)
    return apk


def ensure_installed(run: AdbRun) -> None:
    """Install the helper unless the phone already holds this exact build."""
    version = source_hash()
    info = run("shell", "dumpsys", "package", PACKAGE)
    if f"versionName={version}" in info:
        return
    run("install", "-r", "-t", str(build()), timeout=120.0)


def parse_result(output: str) -> str:
    """Pull the XML out of ``am instrument -w`` output, or raise its error."""
    for line in output.splitlines():
        if line.startswith("INSTRUMENTATION_RESULT: xml="):
            return line.split("=", 1)[1]
    for line in output.splitlines():
        if line.startswith("INSTRUMENTATION_RESULT: error="):
            msg = f"a11y helper failed: {line.split('=', 1)[1]}"
            raise UiAutomationError(msg)
    msg = f"a11y helper returned no tree:\n{output.strip()[-500:]}"
    raise UiAutomationError(msg)


@contextlib.contextmanager
def _one_at_a_time(phone: str) -> Iterator[None]:
    """Hold this host's lock on the helper for one phone.

    Android runs one instrumentation per package: a second ``am instrument``
    force-stops the first ("stop ... due to start instr"), and so does an
    ``install -r``. Two sessions dumping at once killed each other's dump in
    the 2026-09-25 live test. A dump takes well under a second, so queueing
    costs nothing noticeable; closing the file releases the lock.
    """
    path = cache_dir() / f"a11ydump-{phone}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def dump_display(run: AdbRun, display: int, phone: str = "any") -> str:
    """Return ``display``'s accessibility tree as uiautomator-style XML."""
    with _one_at_a_time(phone):
        ensure_installed(run)
        output = run(
            "shell",
            "am",
            "instrument",
            "-w",
            "-e",
            "display",
            str(display),
            _RUNNER,
            timeout=45.0,
        )
    return parse_result(output)
