"""Launcher names for every registered app, and the rules they must meet.

kuhy's rules (2026-10-23): a name starts with a capital, holds only ASCII
letters -- no spaces, underscores or punctuation -- and is short enough that
the Pixel launcher never truncates it with an ellipsis. ``signalbot_remote``
showed as ``signalbot_r...`` while the 12-character ``Daily limits`` fitted.
A character cap alone was not enough: the 10-letter ``FocusOwner`` was still
cut in the app drawer, so the rendered width in the launcher font is capped
too (:mod:`_label_widths`).

``repo_contract`` (kuhyx/utils) applies the same rules to every Flutter repo's
``android:label``, so an app that is not registered here is still held to them.
"""

from __future__ import annotations

import re
from typing import Final

from python_pkg.app_icons._label_widths import MAX_WIDTH, label_width

MAX_LENGTH: Final[int] = 10

_ASCII_LETTERS: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]+")

LABELS: Final[dict[str, str]] = {
    "dufs_client": "Cloud",
    "focus_owner": "Focuser",
    "workout_app": "Workout",
    "wake_alarm_sync": "WakeAlarm",
    "diet_guard_app": "DietGuard",
    "todo": "Todo",
    "untools": "Untools",
    "punchme": "PunchMe",
    "restaurant_rater": "Rater",
    "habit_stack": "HabitStack",
    "home_inventory": "Inventory",
    "epopeja_karta": "Epopeja",
    "octoforge": "OctoForge",
    "kuhylog": "KuhyLog",
    "lyricanki": "LyricAnki",
    "betting_sim": "BettingSim",
    "home_guard_app": "Homer",
    "signalbot_remote": "SignalBot",
    "umbrella": "Umbrella",
    "book_guard_app": "BookGuard",
    "daily_limits": "DailyLimit",
    "tutor": "Tutor",
    "tunedeck": "TuneDeck",
    "sufler": "Sufler",
    "macro_cam": "MacroCam",
}


def label_problems(name: str) -> list[str]:
    """List every launcher-name rule a name breaks.

    Parameters:
    name (str): Candidate launcher label.

    Returns:
    list[str]: One message per broken rule; empty when the name is valid.
    """
    if not name:
        return ["label is empty"]
    problems: list[str] = []
    letters_only = _ASCII_LETTERS.fullmatch(name) is not None
    if not letters_only:
        problems.append(
            f"{name!r} must contain only ASCII letters (no spaces, _ or symbols)"
        )
    if not name[0].isupper():
        problems.append(f"{name!r} must start with a capital letter")
    # The width table only knows ASCII letters; other names already failed.
    if letters_only and label_width(name) > MAX_WIDTH:
        problems.append(
            f"{name!r} is {label_width(name)} wide in the launcher font; "
            f"at most {MAX_WIDTH} fit"
        )
    if len(name) > MAX_LENGTH:
        problems.append(
            f"{name!r} has {len(name)} characters; at most {MAX_LENGTH} fit"
        )
    return problems
