"""Tests for translator module - part 2 (languages, file I/O, CLI, integration)."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.word_frequency import translator
from python_pkg.word_frequency._translator_helpers import (
    format_translations,
    read_file,
)
from python_pkg.word_frequency.tests._translator_helpers import ArgosAvailableMock
from python_pkg.word_frequency.translator import (
    download_languages,
    get_available_packages,
    get_installed_languages,
    main,
    translate_words,
)

if TYPE_CHECKING:
    from pathlib import Path

# get_installed_languages tests


class TestGetInstalledLanguages:
    """Tests for get_installed_languages function."""

    def test_argos_unavailable(self, mock_argos_unavailable: None) -> None:
        """Test when argos is unavailable."""
        result = get_installed_languages()
        assert result == []

    def test_returns_languages(self) -> None:
        """Test returning installed languages."""
        mock_lang1 = MagicMock()
        mock_lang1.code = "en"
        mock_lang1.name = "English"
        mock_lang2 = MagicMock()
        mock_lang2.code = "es"
        mock_lang2.name = "Spanish"

        # We need to mock the translate module's get_installed_languages
        mock_translate_module = MagicMock()
        mock_translate_module.get_installed_languages.return_value = [
            mock_lang1,
            mock_lang2,
        ]
        mock_package_module = MagicMock()
        mock_parent = MagicMock()
        mock_parent.translate = mock_translate_module
        mock_parent.package = mock_package_module

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.translate": mock_translate_module,
                    "argostranslate.package": mock_package_module,
                },
            ),
        ):
            result = get_installed_languages()

        assert ("en", "English") in result
        assert ("es", "Spanish") in result


# get_available_packages tests


class TestGetAvailablePackages:
    """Tests for get_available_packages function."""

    def test_argos_unavailable(self, mock_argos_unavailable: None) -> None:
        """Test when argos is unavailable."""
        result = get_available_packages()
        assert result == []


# download_languages tests


class TestDownloadLanguages:
    """Tests for download_languages function."""

    def test_argos_unavailable(self, mock_argos_unavailable: None) -> None:
        """Test when argos is unavailable."""
        result = download_languages(["en", "es"])
        assert result == {}


# read_file tests


class TestReadFile:
    """Tests for read_file function."""

    def test_read_file(self, tmp_path: Path) -> None:
        """Test reading a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello\nworld", encoding="utf-8")

        content = read_file(test_file)

        assert content == "hello\nworld"

    def test_read_file_not_found(self, tmp_path: Path) -> None:
        """Test reading non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_file(tmp_path / "nonexistent.txt")


# main function tests


class TestMain:
    """Tests for main CLI function."""

    def test_argos_unavailable_error(self, mock_argos_unavailable: None) -> None:
        """Test error when argos not installed."""
        result = main(["--text", "hello", "--from", "en", "--to", "es"])
        assert result == 1

    def test_list_languages_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test listing languages when none installed."""
        mock_translate_module = MagicMock()
        mock_translate_module.get_installed_languages.return_value = []
        mock_package_module = MagicMock()
        mock_parent = MagicMock()
        mock_parent.translate = mock_translate_module
        mock_parent.package = mock_package_module

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.translate": mock_translate_module,
                    "argostranslate.package": mock_package_module,
                },
            ),
        ):
            result = main(["--list-languages"])

        assert result == 0
        captured = capsys.readouterr()
        assert "No languages installed" in captured.out

    def test_list_languages_with_results(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test listing installed languages."""
        mock_lang = MagicMock()
        mock_lang.code = "en"
        mock_lang.name = "English"

        mock_translate_module = MagicMock()
        mock_translate_module.get_installed_languages.return_value = [mock_lang]
        mock_package_module = MagicMock()
        mock_parent = MagicMock()
        mock_parent.translate = mock_translate_module
        mock_parent.package = mock_package_module

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.translate": mock_translate_module,
                    "argostranslate.package": mock_package_module,
                },
            ),
        ):
            result = main(["--list-languages"])

        assert result == 0
        captured = capsys.readouterr()
        assert "en" in captured.out
        assert "English" in captured.out

    def test_translate_single_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test translating single text."""
        with ArgosAvailableMock("hola"):
            result = main(["--text", "hello", "--from", "en", "--to", "es"])

        assert result == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out
        assert "hola" in captured.out

    def test_translate_multiple_words(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test translating multiple words."""
        with ArgosAvailableMock(["hola", "mundo"]):
            result = main(["--words", "hello", "world", "--from", "en", "--to", "es"])

        assert result == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out
        assert "world" in captured.out

    def test_translate_from_file(
        self,
        temp_words_file: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test translating words from file."""
        with ArgosAvailableMock(["hola", "mundo", "adios"]):
            result = main(
                ["--words-file", str(temp_words_file), "--from", "en", "--to", "es"]
            )

        assert result == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out
        assert "world" in captured.out
        assert "goodbye" in captured.out

    def test_translate_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error when words file not found."""
        with ArgosAvailableMock():
            result = main(
                ["--words-file", "/nonexistent/file.txt", "--from", "en", "--to", "es"]
            )

        assert result == 1
        captured = capsys.readouterr()
        assert "File not found" in captured.err

    def test_translate_output_to_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Test outputting translations to file."""
        output_file = tmp_path / "output.txt"

        with ArgosAvailableMock("hola"):
            result = main(
                [
                    "--text",
                    "hello",
                    "--from",
                    "en",
                    "--to",
                    "es",
                    "--output",
                    str(output_file),
                ]
            )

        assert result == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "hello" in content
        assert "hola" in content

    def test_no_input_shows_help(
        self,
    ) -> None:
        """Test that no input shows help."""
        with ArgosAvailableMock():
            result = main([])

        assert result == 1

    def test_translation_failure_returns_error(self) -> None:
        """Test that translation failure returns error code when argos unavailable."""
        with patch.object(
            translator,
            "_ensure_argos_installed",
            side_effect=ImportError("argostranslate not available"),
        ):
            result = main(["--text", "hello", "--from", "en", "--to", "es"])
        assert result == 1


# Integration-style tests (still mocked but testing more flow)


class TestIntegration:
    """Integration-style tests for translator."""

    def test_full_translation_flow(self) -> None:
        """Test complete translation flow."""
        with ArgosAvailableMock(["uno", "dos", "tres"]) as mock:
            mock.side_effect = ["uno", "dos", "tres"]
            words = ["one", "two", "three"]
            results = translate_words(words, "en", "es", use_cache=False)

        assert all(r.success for r in results)
        assert [r.translated_word for r in results] == ["uno", "dos", "tres"]

        output = format_translations(results)
        assert "en -> es" in output
        assert "one" in output
        assert "uno" in output


class TestGetAvailablePackagesWithArgos:
    """Tests for get_available_packages with argos available."""

    def test_returns_packages(self) -> None:
        pkg = MagicMock()
        pkg.from_code = "en"
        pkg.from_name = "English"
        pkg.to_code = "es"
        pkg.to_name = "Spanish"

        mock_package = MagicMock()
        mock_package.update_package_index.return_value = None
        mock_package.get_available_packages.return_value = [pkg]
        mock_translate = MagicMock()
        mock_parent = MagicMock()
        mock_parent.package = mock_package
        mock_parent.translate = mock_translate

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.package": mock_package,
                    "argostranslate.translate": mock_translate,
                },
            ),
        ):
            result = get_available_packages()
        assert result == [("en", "English", "es", "Spanish")]


class TestDownloadLanguagesFull:
    """Tests for download_languages with full flow."""

    def test_downloads_packages(self) -> None:
        pkg = MagicMock()
        pkg.from_code = "en"
        pkg.to_code = "es"
        pkg.download.return_value = tempfile.gettempdir() + "/fake.argosmodel"

        mock_package = MagicMock()
        mock_package.update_package_index.return_value = None
        mock_package.get_available_packages.return_value = [pkg]
        mock_translate = MagicMock()
        mock_parent = MagicMock()
        mock_parent.package = mock_package
        mock_parent.translate = mock_translate

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.package": mock_package,
                    "argostranslate.translate": mock_translate,
                },
            ),
        ):
            result = download_languages(["en", "es"])
        assert "en->es" in result
        assert result["en->es"] is True

    def test_package_not_available(self) -> None:
        mock_package = MagicMock()
        mock_package.update_package_index.return_value = None
        mock_package.get_available_packages.return_value = []
        mock_translate = MagicMock()
        mock_parent = MagicMock()
        mock_parent.package = mock_package
        mock_parent.translate = mock_translate

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.package": mock_package,
                    "argostranslate.translate": mock_translate,
                },
            ),
        ):
            result = download_languages(["en", "es"])
        # No packages available, both directions fail
        assert result.get("en->es") is False

    def test_download_failure(self) -> None:
        pkg = MagicMock()
        pkg.from_code = "en"
        pkg.to_code = "es"
        pkg.download.side_effect = OSError("download failed")

        mock_package = MagicMock()
        mock_package.update_package_index.return_value = None
        mock_package.get_available_packages.return_value = [pkg]
        mock_translate = MagicMock()
        mock_parent = MagicMock()
        mock_parent.package = mock_package
        mock_parent.translate = mock_translate

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.package": mock_package,
                    "argostranslate.translate": mock_translate,
                },
            ),
        ):
            result = download_languages(["en", "es"])
        assert result["en->es"] is False


class TestTranslateWordCache:
    """Tests for translate_word with cache interactions."""

    def test_cache_hit(self) -> None:
        mock_cache = MagicMock()
        mock_cache.get.return_value = "hola"

        with (
            patch.object(translator, "get_translation_cache", return_value=mock_cache),
            patch.object(translator, "_ensure_argos_installed"),
        ):
            from python_pkg.word_frequency.translator import translate_word

            result = translate_word("hello", "en", "es", use_cache=True)
        assert result.success is True
        assert result.translated_word == "hola"

    def test_cache_set_after_translation(self) -> None:
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        with (
            ArgosAvailableMock("hola"),
            patch.object(translator, "get_translation_cache", return_value=mock_cache),
        ):
            from python_pkg.word_frequency.translator import translate_word

            result = translate_word("hello", "en", "es", use_cache=True)
        assert result.success is True
        mock_cache.set.assert_called_once()
