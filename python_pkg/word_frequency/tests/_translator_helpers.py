"""Shared test helpers for translator tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.word_frequency import translator


class ArgosAvailableMock:
    """Context manager to mock argostranslate being available and control its output.

    Works whether argos is installed or not by patching sys.modules.
    """

    def __init__(
        self, translate_returns: str | list[str] | Exception | None = None
    ) -> None:
        """Initialize with return values for translate()."""
        self.translate_returns = translate_returns
        self.mock_translate_fn = MagicMock()
        self.mock_translate_module = MagicMock()
        self.mock_package_module = MagicMock()
        self.mock_parent = MagicMock()
        self._sys_modules_patcher: MagicMock | None = None
        self._ensure_patcher: MagicMock | None = None
        self._lang_patcher: MagicMock | None = None
        self._check_argos_patcher: MagicMock | None = None
        self._argos_module_patcher: MagicMock | None = None

    def __enter__(self) -> MagicMock:
        """Set up the mocks."""
        # Set up translate return value
        if isinstance(self.translate_returns, Exception | list):
            self.mock_translate_fn.side_effect = self.translate_returns
        elif self.translate_returns is not None:
            self.mock_translate_fn.return_value = self.translate_returns

        # Wire up the mock modules
        self.mock_translate_module.translate = self.mock_translate_fn
        self.mock_translate_module.get_installed_languages = MagicMock(return_value=[])
        self.mock_package_module.update_package_index = MagicMock()
        self.mock_package_module.get_available_packages = MagicMock(return_value=[])
        self.mock_parent.translate = self.mock_translate_module
        self.mock_parent.package = self.mock_package_module

        # Patch sys.modules to inject our mock (works even if argos not installed)
        self._sys_modules_patcher = patch.dict(
            "sys.modules",
            {
                "argostranslate": self.mock_parent,
                "argostranslate.translate": self.mock_translate_module,
                "argostranslate.package": self.mock_package_module,
            },
        )

        # Patch the module-level argostranslate reference in translator
        self._argos_module_patcher = patch.object(
            translator, "argostranslate", self.mock_parent, create=True
        )

        # Patch _ensure_argos_installed and _ensure_language_pair to no-op
        self._ensure_patcher = patch.object(
            translator, "_ensure_argos_installed", lambda: None
        )
        self._lang_patcher = patch.object(
            translator, "_ensure_language_pair", lambda _f, _t: None
        )
        self._check_argos_patcher = patch.object(
            translator, "_check_argos", return_value=True
        )

        self._sys_modules_patcher.start()
        self._argos_module_patcher.start()
        self._ensure_patcher.start()
        self._lang_patcher.start()
        self._check_argos_patcher.start()

        return self.mock_translate_fn

    def __exit__(self, *args: object) -> None:
        """Restore original state."""
        if self._check_argos_patcher:
            self._check_argos_patcher.stop()
        if self._lang_patcher:
            self._lang_patcher.stop()
        if self._ensure_patcher:
            self._ensure_patcher.stop()
        if self._argos_module_patcher:
            self._argos_module_patcher.stop()
        if self._sys_modules_patcher:
            self._sys_modules_patcher.stop()
