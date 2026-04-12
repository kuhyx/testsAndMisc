"""Tests for python_pkg.fm24_searcher.models."""

from __future__ import annotations

from python_pkg.fm24_searcher.models import (
    ALL_VISIBLE_ATTRS,
    GOALKEEPER_ATTRS,
    MENTAL_ATTRS,
    PHYSICAL_ATTRS,
    TECHNICAL_ATTRS,
    Player,
)


class TestAttributeLists:
    """Attribute list sanity checks."""

    def test_technical_count(self) -> None:
        assert len(TECHNICAL_ATTRS) == 14

    def test_mental_count(self) -> None:
        assert len(MENTAL_ATTRS) == 14

    def test_physical_count(self) -> None:
        assert len(PHYSICAL_ATTRS) == 8

    def test_goalkeeper_count(self) -> None:
        assert len(GOALKEEPER_ATTRS) == 13

    def test_all_visible_is_concat(self) -> None:
        assert ALL_VISIBLE_ATTRS == (TECHNICAL_ATTRS + MENTAL_ATTRS + PHYSICAL_ATTRS)


class TestPlayerDefaults:
    """Player dataclass default values."""

    def test_defaults(self) -> None:
        p = Player()
        assert p.uid == 0
        assert p.name == ""
        assert p.date_of_birth == ""
        assert p.nationality == ""
        assert p.club == ""
        assert p.position == ""
        assert p.current_ability == 0
        assert p.potential_ability == 0
        assert p.personality == []
        assert p.attributes == {}
        assert p.gk_attributes == {}
        assert p.value == ""
        assert p.wage == ""
        assert p.source == ""


class TestGetAttr:
    """Player.get_attr() method."""

    def test_present(self) -> None:
        p = Player(attributes={"Pace": 18})
        assert p.get_attr("Pace") == 18

    def test_missing(self) -> None:
        p = Player(attributes={"Pace": 18})
        assert p.get_attr("Strength") == 0


class TestWeightedScore:
    """Player.weighted_score() method."""

    def test_basic_score(self) -> None:
        p = Player(attributes={"Pace": 18, "Stamina": 12})
        score = p.weighted_score({"Pace": 2.0, "Stamina": 1.0})
        expected = (18 * 2.0 + 12 * 1.0) / (2.0 + 1.0)
        assert score == expected

    def test_zero_weight_sum(self) -> None:
        p = Player()
        assert p.weighted_score({"Pace": 0.0}) == 0.0

    def test_missing_attrs_ignored(self) -> None:
        p = Player(attributes={"Pace": 10})
        score = p.weighted_score({"Pace": 1.0, "Stamina": 1.0})
        # Stamina=0 so val > 0 is False → not counted.
        assert score == 10.0 / 1.0

    def test_empty_weights(self) -> None:
        p = Player(attributes={"Pace": 18})
        assert p.weighted_score({}) == 0.0


class TestMatchesFilter:
    """Player.matches_filter() method."""

    def test_no_filters(self) -> None:
        p = Player(name="Test")
        assert p.matches_filter() is True

    def test_min_attrs_pass(self) -> None:
        p = Player(attributes={"Pace": 15, "Stamina": 12})
        assert p.matches_filter(min_attrs={"Pace": 10}) is True

    def test_min_attrs_fail(self) -> None:
        p = Player(attributes={"Pace": 5})
        assert p.matches_filter(min_attrs={"Pace": 10}) is False

    def test_min_ca_pass(self) -> None:
        p = Player(current_ability=150)
        assert p.matches_filter(min_ca=100) is True

    def test_min_ca_fail(self) -> None:
        p = Player(current_ability=50)
        assert p.matches_filter(min_ca=100) is False

    def test_min_ca_zero_skipped(self) -> None:
        p = Player(current_ability=0)
        assert p.matches_filter(min_ca=0) is True

    def test_position_filter_pass(self) -> None:
        p = Player(position="AMC, MC")
        assert p.matches_filter(position_filter="mc") is True

    def test_position_filter_fail(self) -> None:
        p = Player(position="DC")
        assert p.matches_filter(position_filter="amc") is False

    def test_nationality_filter_pass(self) -> None:
        p = Player(nationality="England")
        assert p.matches_filter(nationality_filter="eng") is True

    def test_nationality_filter_fail(self) -> None:
        p = Player(nationality="France")
        assert p.matches_filter(nationality_filter="eng") is False

    def test_club_filter_pass(self) -> None:
        p = Player(club="Manchester United")
        assert p.matches_filter(club_filter="man") is True

    def test_club_filter_fail(self) -> None:
        p = Player(club="Liverpool")
        assert p.matches_filter(club_filter="man") is False

    def test_no_filter_matches_all(self) -> None:
        p = Player()
        assert p.matches_filter() is True

    def test_combined_filters(self) -> None:
        p = Player(
            current_ability=170,
            position="AMC",
            nationality="Brazil",
            club="Real Madrid",
            attributes={"Dribbling": 18},
        )
        assert p.matches_filter(
            min_attrs={"Dribbling": 15},
            min_ca=150,
            position_filter="amc",
            nationality_filter="bra",
            club_filter="real",
        )
