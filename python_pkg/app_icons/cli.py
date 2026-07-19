"""Command-line entry point for the shared app-icon generator.

Usage:
    PYTHONPATH=~/testsAndMisc python -m python_pkg.app_icons list
    PYTHONPATH=~/testsAndMisc python -m python_pkg.app_icons preview -o sheet.png
    PYTHONPATH=~/testsAndMisc python -m python_pkg.app_icons generate --app todo
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from python_pkg.app_icons import apps, generate, glyphs, preview, render, style


def _emit(message: str) -> None:
    """Write a line to stdout.

    Parameters:
    message (str): Line to write, without a trailing newline.
    """
    sys.stdout.write(f"{message}\n")


def _add_app_argument(parser: argparse.ArgumentParser) -> None:
    """Attach the repeatable ``--app`` selector to a subparser.

    Parameters:
    parser (argparse.ArgumentParser): Subparser to extend.
    """
    parser.add_argument(
        "--app",
        action="append",
        dest="app_keys",
        choices=sorted(apps.APPS),
        help="app to act on; repeatable. Defaults to every registered app.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Returns:
    argparse.ArgumentParser: Parser with the ``list``, ``preview`` and
        ``generate`` subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="python -m python_pkg.app_icons",
        description="Generate on-style launcher icons for kuhy's Flutter apps.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="show registered apps and available glyphs")

    preview_parser = subparsers.add_parser(
        "preview", help="render a contact sheet for visual review"
    )
    _add_app_argument(preview_parser)
    preview_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("icon_review_sheet.png"),
        help="where to write the contact sheet",
    )

    generate_parser = subparsers.add_parser(
        "generate", help="write icon assets into the app repositories"
    )
    _add_app_argument(generate_parser)
    generate_parser.add_argument(
        "--android",
        action="store_true",
        help="also run flutter_launcher_icons to rebuild the Android mipmaps",
    )
    generate_parser.add_argument(
        "--linux-out",
        type=Path,
        default=None,
        help=(
            "directory to write hicolor PNGs into for apps with a Linux target; "
            "skipped when omitted"
        ),
    )
    return parser


def _selected(app_keys: list[str] | None) -> list[str]:
    """Resolve the ``--app`` selection to a concrete ordered list.

    Parameters:
    app_keys (list[str] | None): Keys given on the command line, if any.

    Returns:
    list[str]: Keys to act on, in registry order.
    """
    if app_keys:
        return [key for key in apps.APPS if key in set(app_keys)]
    return list(apps.APPS)


def _cmd_list() -> int:
    """Print the app registry and glyph library.

    Returns:
    int: Process exit status.
    """
    _emit("Apps:")
    for app in apps.APPS.values():
        linux = " +linux" if app.linux else ""
        _emit(f"  {app.key:16} {app.accent}  {app.glyph}{linux}  {app.repo}")
    _emit("\nGlyphs:")
    for glyph in glyphs.GLYPHS.values():
        _emit(f"  {glyph.name:16} {glyph.description}")
    return 0


def _cmd_preview(app_keys: list[str] | None, output: Path) -> int:
    """Render the review contact sheet.

    Parameters:
    app_keys (list[str] | None): Selection from the command line.
    output (Path): Where to write the sheet.

    Returns:
    int: Process exit status.
    """
    sheet = preview.build_contact_sheet(_selected(app_keys), output)
    _emit(f"wrote {sheet}")
    return 0


def _cmd_generate(
    app_keys: list[str] | None,
    *,
    android: bool,
    linux_out: Path | None,
) -> int:
    """Write icon assets, optionally driving the platform generators.

    Parameters:
    app_keys (list[str] | None): Selection from the command line.
    android (bool): Run flutter_launcher_icons afterwards.
    linux_out (Path | None): Directory for hicolor PNGs, or None to skip.

    Returns:
    int: Process exit status.
    """
    for key in _selected(app_keys):
        app = apps.get_app(key)
        written = generate.write_assets(app)
        _emit(f"{app.key}: wrote {len(written)} asset files to {app.asset_dir}")

        overflow = render.safe_box_overflow(glyphs.get_glyph(app.glyph), app.accent)
        if any(overflow):
            _emit(
                f"  warning: glyph exceeds the {style.SAFE_BOX}px safe box "
                f"by {overflow[0]}x{overflow[1]}px; a launcher mask may clip it"
            )

        if linux_out is not None and app.linux:
            icons = generate.write_linux_icons(app, linux_out)
            _emit(f"  wrote {len(icons)} hicolor PNGs to {linux_out}")

        if android:
            generate.run_flutter_launcher_icons(app)
            _emit("  regenerated Android mipmaps")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Parameters:
    argv (list[str] | None): Arguments to parse; defaults to ``sys.argv[1:]``.

    Returns:
    int: Process exit status.
    """
    args = build_parser().parse_args(argv)
    if args.command == "list":
        return _cmd_list()
    if args.command == "preview":
        return _cmd_preview(args.app_keys, args.output)
    return _cmd_generate(
        args.app_keys,
        android=args.android,
        linux_out=args.linux_out,
    )
