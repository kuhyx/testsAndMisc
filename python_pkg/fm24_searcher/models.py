"""Data model for FM24 players."""

from __future__ import annotations

from dataclasses import dataclass, field

# FM24 visible attribute names grouped by category.
TECHNICAL_ATTRS: list[str] = [
    "Corners",
    "Crossing",
    "Dribbling",
    "Finishing",
    "First Touch",
    "Free Kick",
    "Heading",
    "Long Shots",
    "Long Throws",
    "Marking",
    "Passing",
    "Penalty Taking",
    "Tackling",
    "Technique",
]

MENTAL_ATTRS: list[str] = [
    "Aggression",
    "Anticipation",
    "Bravery",
    "Composure",
    "Concentration",
    "Decisions",
    "Determination",
    "Flair",
    "Leadership",
    "Off The Ball",
    "Positioning",
    "Teamwork",
    "Vision",
    "Work Rate",
]

PHYSICAL_ATTRS: list[str] = [
    "Acceleration",
    "Agility",
    "Balance",
    "Jumping Reach",
    "Natural Fitness",
    "Pace",
    "Stamina",
    "Strength",
]

GOALKEEPER_ATTRS: list[str] = [
    "Aerial Reach",
    "Command of Area",
    "Communication",
    "Eccentricity",
    "First Touch (GK)",
    "Handling",
    "Kicking",
    "One on Ones",
    "Passing (GK)",
    "Punching (Tendency)",
    "Reflexes",
    "Rushing Out (Tendency)",
    "Throwing",
]

ALL_VISIBLE_ATTRS: list[str] = TECHNICAL_ATTRS + MENTAL_ATTRS + PHYSICAL_ATTRS


@dataclass
class Player:
    """A single FM24 player record."""

    # Identity (from binary or HTML).
    uid: int = 0
    name: str = ""

    # Biographical.
    date_of_birth: str = ""  # ISO format YYYY-MM-DD
    nationality: str = ""
    club: str = ""
    position: str = ""

    # Ability ratings (from binary — may be approximate).
    current_ability: int = 0
    potential_ability: int = 0

    # Hidden personality bytes (from binary).
    personality: list[int] = field(default_factory=list)

    # Visible attributes (1-20 scale). Key = attribute name.
    attributes: dict[str, int] = field(default_factory=dict)

    # Goalkeeper attributes.
    gk_attributes: dict[str, int] = field(default_factory=dict)

    # Monetary values.
    value: str = ""
    wage: str = ""

    # Data source for traceability.
    source: str = ""  # "binary", "html", or "merged"

    def get_attr(self, name: str) -> int:
        """Get an attribute value by name, 0 if missing."""
        return self.attributes.get(name, 0)

    def weighted_score(
        self,
        weights: dict[str, float],
    ) -> float:
        """Compute weighted attribute score for scouting."""
        total = 0.0
        weight_sum = 0.0
        for attr_name, weight in weights.items():
            val = self.get_attr(attr_name)
            if val > 0:
                total += val * weight
                weight_sum += weight
        if weight_sum == 0:
            return 0.0
        return total / weight_sum

    def matches_filter(
        self,
        min_attrs: dict[str, int] | None = None,
        min_ca: int | None = None,
        position_filter: str | None = None,
        nationality_filter: str | None = None,
        club_filter: str | None = None,
    ) -> bool:
        """Check if this player matches all given filters."""
        if min_attrs:
            for attr_name, min_val in min_attrs.items():
                if self.get_attr(attr_name) < min_val:
                    return False
        if min_ca and self.current_ability < min_ca:
            return False
        if position_filter and position_filter.lower() not in (self.position.lower()):
            return False
        if nationality_filter and nationality_filter.lower() not in (
            self.nationality.lower()
        ):
            return False
        return not (club_filter and club_filter.lower() not in self.club.lower())
