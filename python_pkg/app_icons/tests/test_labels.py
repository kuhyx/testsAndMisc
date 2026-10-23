"""Tests for app_icons.labels: the launcher-name rules every app must meet."""

from __future__ import annotations

import pytest

from python_pkg.app_icons import apps, labels


class TestLabelProblems:
    @pytest.mark.parametrize("name", ["Todo", "BookGuard", "WakeAlarm", "Focuser", "A"])
    def test_valid(self, name: str) -> None:
        assert labels.label_problems(name) == []

    @pytest.mark.parametrize(
        ("name", "fragment"),
        [
            ("", "empty"),
            ("todo", "capital"),
            ("Book Guard", "ASCII letters"),
            ("diet_guard", "ASCII letters"),
            ("Umbrella?", "ASCII letters"),
            ("Żółw", "ASCII letters"),
            ("SignalBotRemote", "characters"),
            ("FocusOwner", "launcher font"),
            ("WakeAlarmX", "launcher font"),
        ],
    )
    def test_invalid(self, name: str, fragment: str) -> None:
        assert any(fragment in p for p in labels.label_problems(name))


class TestRegistryLabels:
    def test_every_app_has_a_label(self) -> None:
        assert set(labels.LABELS) == set(apps.APPS)

    @pytest.mark.parametrize("key", sorted(apps.APPS))
    def test_label_is_valid(self, key: str) -> None:
        assert labels.label_problems(apps.get_app(key).label) == []

    def test_labels_are_unique(self) -> None:
        assert len(set(labels.LABELS.values())) == len(labels.LABELS)
