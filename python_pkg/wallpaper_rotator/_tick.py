"""One timer tick: rotate or refresh the background, then remember it."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import random
import re
import subprocess
from typing import cast

import numpy as np

from python_pkg.wallpaper_rotator import _paint
from python_pkg.wallpaper_rotator._context import DEFAULT_CACHE, RenderContext
from python_pkg.wallpaper_rotator._rotation import State, plan
from python_pkg.wallpaper_rotator.styles import STYLES

ROOT_IMAGE = DEFAULT_CACHE / "root.png"
STATE_FILE = DEFAULT_CACHE / "state.json"
# X writes its server pid to <tmp>/.X<display>-lock.
_X_LOCK_DIR = Path("/") / "tmp"
_PIXMAP = re.compile(r"#\s*(0x[0-9a-f]+)")


def i3_outputs() -> list[dict[str, object]]:
    """Return ``i3-msg -t get_outputs`` as parsed JSON."""
    out = subprocess.run(
        ["/usr/bin/i3-msg", "-t", "get_outputs"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return cast("list[dict[str, object]]", json.loads(out))


def root_identity(display: str | None = None) -> str | None:
    """Identify the root pixmap now shown: X server pid plus pixmap id.

    The pid (from the X lock file) changes with every X session, so a fresh
    login never matches a pixmap id saved in an earlier one. ``None`` means
    no background is set at all.
    """
    display = display or os.environ.get("DISPLAY", ":0")
    number = display.lstrip(":").split(".")[0]
    try:
        server = (_X_LOCK_DIR / f".X{number}-lock").read_text(encoding="utf-8").strip()
    except OSError:
        server = "?"
    prop = subprocess.run(
        ["/usr/bin/xprop", "-root", "_XROOTPMAP_ID"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout
    found = _PIXMAP.search(prop)
    return f"{server}:{found.group(1)}" if found else None


def tick(rng: random.Random | None = None) -> bool:
    """Run one tick; return whether the background was repainted."""
    rects = _paint.layout(i3_outputs())
    ctx = RenderContext.live()
    names = [name for name, style in STYLES.items() if style.available(ctx)]
    state, paint = plan(
        State.load(STATE_FILE),
        list(rects),
        ctx.now,
        names,
        rng or random.SystemRandom(),
        root_id=root_identity(),
    )
    if paint:
        images = {
            output: STYLES[pick.style].render(
                ctx,
                (rects[output][2], rects[output][3]),
                np.random.default_rng(pick.seed),
            )
            for output, pick in state.picks.items()
            if output in rects
        }
        _paint.apply(_paint.compose(rects, images), ROOT_IMAGE)
        state = replace(state, root_id=root_identity())
    state.save(STATE_FILE)
    return paint
