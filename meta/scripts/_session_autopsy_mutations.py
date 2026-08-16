#!/usr/bin/env python3
"""The mutation operators: one named defect each, injected into a hook copy.

Split out of ``mutate_session_autopsy_hooks.py`` to keep both files under the
repository's 250-line cap. Every function here takes the text of one hook and
returns it with exactly one guard broken; the driver applies them one at a time
and records which tests notice.

Nothing here touches the filesystem -- these are pure text transforms, which is
what makes the driver's "the deployed hooks are never modified" guarantee easy
to see.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

END_HOOK = "session_autopsy_end.sh"
START_HOOK = "session_autopsy_start.sh"
_GUTTED = "#!/bin/bash\nexit 0\n"


def _gut(_text: str) -> str:
    """Replace an entire hook body with a bare successful exit."""
    return _GUTTED


def _drop_transcript_guard(text: str) -> str:
    """Remove the SessionEnd guard that requires an existing transcript."""
    return re.sub(
        r'if \[\[ -z "\$transcript".*?\nfi\n',
        "",
        text,
        flags=re.DOTALL,
    )


def _widen_count(text: str) -> str:
    """Make a zero candidate count announce itself."""
    return text.replace("(( count > 0 ))", "(( count >= 0 ))")


def _drop_numeric_guard(text: str) -> str:
    """Drop the count regex guard, leaving the arithmetic syntactically valid."""
    return text.replace(
        '[[ "$count" =~ ^[0-9]+$ ]] && (( count > 0 ))',
        "(( count > 0 ))",
    )


def _drop_readable_guard(text: str) -> str:
    """Remove the early exit taken when the state file cannot be read."""
    return re.sub(
        r'if \[\[ ! -r "\$STATE" \]\]; then\n.*?\nfi\n',
        "",
        text,
        flags=re.DOTALL,
    )


def _always_announce(text: str) -> str:
    """Announce unconditionally -- the defect every silence test exists to catch."""
    return re.sub(r'if \[\[ "\$count".*?; then', "if true; then", text)


def _unguarded_and_always_announce(text: str) -> str:
    """Drop the readability guard AND announce unconditionally.

    Needed because the readability guard is redundant on its own: jq's stderr is
    suppressed and an empty count already fails the arithmetic, so removing it
    changes nothing observable. Only removing it together with the count
    condition can reach the no-state and unreadable-state cases.
    """
    return _always_announce(_drop_readable_guard(text))


class Mutation(NamedTuple):
    """One named defect injected into one hook."""

    name: str
    hook: str
    apply: Callable[[str], str]


MUTATIONS = (
    Mutation("gut-end", END_HOOK, _gut),
    Mutation("gut-start", START_HOOK, _gut),
    Mutation("end-no-transcript-guard", END_HOOK, _drop_transcript_guard),
    Mutation("start-count-ge-zero", START_HOOK, _widen_count),
    Mutation("start-no-numeric-guard", START_HOOK, _drop_numeric_guard),
    Mutation("start-no-readable-guard", START_HOOK, _drop_readable_guard),
    Mutation("start-always-announce", START_HOOK, _always_announce),
    Mutation("start-unguarded-announce", START_HOOK, _unguarded_and_always_announce),
)

__all__ = ["END_HOOK", "MUTATIONS", "START_HOOK", "Mutation"]
