"""Command-line entry point: image + spec in, exit code and JSON out.

Adjudication is by exit code, never by a model judging a model. Three values,
because conflating a harness fault with an art rejection would convert our own
bugs into art verdicts and poison the bake-off metrics:

* 0 -- every applicable gate passed
* 1 -- the asset is well-formed but failed at least one gate
* 2 -- the spec or the image could not be read
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, UnidentifiedImageError

from python_pkg.artgate.codes import (
    EXIT_GATE_FAILURE,
    EXIT_HARNESS_ERROR,
    EXIT_PASS,
    Code,
)
from python_pkg.artgate.contrast import check_silhouette
from python_pkg.artgate.pixels import (
    check_alpha_binary,
    check_color_count,
    check_palette,
    check_scale_invariance,
)
from python_pkg.artgate.spec import SpecError, TargetSpec, load_spec


def evaluate(rgba: np.ndarray, spec: TargetSpec) -> list[Code]:
    """Run every gate the spec declares applicable.

    Gate order matters: alpha binarity is evaluated before the colour count,
    because a soft-alpha image has no fully-opaque pixels and would otherwise
    yield a colour count of zero and pass.

    Args:
        rgba: An ``(h, w, 4)`` uint8 array.
        spec: The target specification.

    Returns:
        The failing reason codes, empty if the asset passes.
    """
    failures: list[Code] = []

    if spec.runs(Code.CANVAS_SIZE) and spec.canvas is not None:
        height, width = rgba.shape[:2]
        if (width, height) != spec.canvas:
            failures.append(Code.CANVAS_SIZE)

    if spec.runs(Code.ALPHA_NOT_BINARY) and spec.alpha_binary:
        failures.extend(check_alpha_binary(rgba))

    if spec.runs(Code.TOO_MANY_COLORS) and spec.max_colors is not None:
        failures.extend(check_color_count(rgba, spec.max_colors))

    if spec.runs(Code.OFF_PALETTE) and spec.palette:
        failures.extend(check_palette(rgba, spec.palette))

    if spec.runs(Code.SCALE_NOT_INVARIANT):
        failures.extend(check_scale_invariance(rgba, spec.scale))

    if spec.runs(Code.SILHOUETTE_LOW_CONTRAST):
        failures.extend(check_silhouette(rgba))

    deduped: list[Code] = []
    for code in failures:
        if code not in deduped:
            deduped.append(code)
    return deduped


def _load_image(path: Path) -> np.ndarray:
    """Read an image as an RGBA uint8 array.

    Args:
        path: Path to the image.

    Returns:
        An ``(h, w, 4)`` uint8 array.

    Raises:
        SpecError: If the file is missing or not a readable image.
    """
    try:
        with Image.open(path) as img:
            return np.asarray(img.convert("RGBA"), dtype=np.uint8)
    except (OSError, UnidentifiedImageError) as exc:
        msg = f"cannot read image {path}: {exc}"
        raise SpecError(msg) from exc


def main(argv: list[str] | None = None) -> int:
    """Gate one image against one spec.

    Args:
        argv: Argument vector, defaulting to ``sys.argv[1:]``.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(
        prog="artgate",
        description="Gate generated game art deterministically.",
    )
    parser.add_argument("image", type=Path, help="PNG to check")
    parser.add_argument("--spec", type=Path, required=True, help="TOML spec")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable verdict on stdout",
    )
    args = parser.parse_args(argv)

    try:
        spec = load_spec(args.spec)
        rgba = _load_image(args.image)
    except SpecError as exc:
        sys.stderr.write(f"artgate: {exc}\n")
        return EXIT_HARNESS_ERROR

    codes = evaluate(rgba, spec)
    status = EXIT_PASS if not codes else EXIT_GATE_FAILURE

    if args.json:
        verdict = {
            "image": str(args.image),
            "style": spec.name,
            "exit": status,
            "codes": [str(c) for c in codes],
        }
        sys.stdout.write(f"{json.dumps(verdict, sort_keys=True)}\n")
    else:
        label = "PASS" if status == EXIT_PASS else "FAIL"
        detail = "" if not codes else " " + ",".join(str(c) for c in codes)
        sys.stdout.write(f"{label} {args.image}{detail}\n")

    return status


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
