"""The fixed subject set the bake-off is pinned to.

Every route and every applicable style is tested on the SAME twelve subjects,
because a route evaluated on easy subjects beats a 50% baseline for free and
the comparison would measure the subject list rather than the route.

The split comes from the `item-icons` skill's measured human verdicts: six
subjects passed and six failed on a first attempt, and the pattern predicting
failure was not drawing difficulty but whether the viewer holds a precise
mental image of the object. That makes the routing rule below falsifiable --
a generator route is predicted to lift specifically the HUMAN_PRIOR six.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class Difficulty(StrEnum):
    """Why a subject is expected to be easy or hard, not how hard to draw."""

    SAFE = "SAFE"
    HUMAN_PRIOR = "HUMAN_PRIOR"
    PRIMITIVE = "PRIMITIVE"

    def __str__(self) -> str:
        """Return the bare value for report tables."""
        return self.value


@dataclass(frozen=True)
class Subject:
    """One bake-off subject.

    Attributes:
        name: Lowercase identifier, used in filenames and report rows.
        difficulty: The predicted failure mode, or SAFE.
        note: Why this subject sits in that category.
    """

    name: str
    difficulty: Difficulty
    note: str


# The six that PASSED in the item-icons measurement: distinctive silhouettes
# with no canonical proportions, so the viewer has a wide error budget.
_SAFE: Final = (
    Subject("key", Difficulty.SAFE, "wards make it unmistakable"),
    Subject("scroll", Difficulty.SAFE, "no canonical proportions"),
    Subject("book", Difficulty.SAFE, "clasp gives it a feature"),
    Subject("bone", Difficulty.SAFE, "organic, no fixed ratio"),
    Subject("gem", Difficulty.SAFE, "facets read at any size"),
    Subject("bomb", Difficulty.SAFE, "fuse is a strong feature"),
)

# The six that FAILED. Kept verbatim so the bake-off measures the same task.
_HARD: Final = (
    Subject("potion", Difficulty.HUMAN_PRIOR, "flask shoulders are specific"),
    Subject("sword", Difficulty.HUMAN_PRIOR, "blade/hilt ratio is known"),
    Subject("shield", Difficulty.PRIMITIVE, "a slab reads as a placeholder"),
    Subject("coin", Difficulty.PRIMITIVE, "a circle with a rim is barebones"),
    Subject("ring", Difficulty.PRIMITIVE, "a torus with no feature"),
    Subject("meat", Difficulty.HUMAN_PRIOR, "a ham has a specific shape"),
)

SUBJECTS: Final = _SAFE + _HARD

# The measured baseline this bake-off must beat: 6 of 12 accepted by a human,
# unchanged after a second redraw round. A cell that cannot beat this is
# reported as such rather than dressed up.
BASELINE_PASS = 6
BASELINE_TOTAL = 12

# item-icons ran two rounds and stayed at 6/12, so a third is not
# evidence-backed. Each cell gets this many rounds, then its number is recorded.
MAX_ROUNDS = 2


def by_name(name: str) -> Subject:
    """Look up a subject.

    Args:
        name: The subject's lowercase identifier.

    Returns:
        The matching subject.

    Raises:
        KeyError: If the name is not part of the fixed set.
    """
    for subject in SUBJECTS:
        if subject.name == name:
            return subject
    msg = f"{name!r} is not one of the {len(SUBJECTS)} fixed subjects"
    raise KeyError(msg)
