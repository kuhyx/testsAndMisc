"""Tests for main() in python_pkg.music_gen.music_generator."""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.music_gen.music_generator import main


class TestMain:
    """Tests for main()."""

    def test_no_prompt_no_interactive_exits(self) -> None:
        with (
            patch("sys.argv", ["music_generator"]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_song_mode(self) -> None:
        with (
            patch(
                "sys.argv",
                ["music_generator", "--song", "la la la", "--music", "pop"],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.generate_song",
            ) as mock_song,
        ):
            main()

        mock_song.assert_called_once_with(
            "la la la",
            "pop",
            voice="v2/en_speaker_6",
            output_dir=None,
        )

    def test_speech_mode(self) -> None:
        with (
            patch("sys.argv", ["music_generator", "--speech", "Hello world"]),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.generate_speech",
            ) as mock_speech,
        ):
            main()

        mock_speech.assert_called_once_with(
            "Hello world",
            voice="v2/en_speaker_6",
            output_dir=None,
        )

    def test_music_mode_with_prompt(self) -> None:
        mock_model = MagicMock()
        mock_processor = MagicMock()

        with (
            patch("sys.argv", ["music_generator", "jazz piano"]),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.select_model_size",
                return_value="small",
            ),
            patch(
                "python_pkg.music_gen.music_generator.load_model",
                return_value=(mock_model, mock_processor),
            ),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
            ) as mock_gen,
        ):
            main()

        mock_gen.assert_called_once_with(
            "jazz piano",
            mock_model,
            mock_processor,
            duration_seconds=10,
            output_dir=None,
        )

    def test_interactive_mode(self) -> None:
        mock_model = MagicMock()
        mock_processor = MagicMock()

        with (
            patch("sys.argv", ["music_generator", "--interactive"]),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.select_model_size",
                return_value="small",
            ),
            patch(
                "python_pkg.music_gen.music_generator.load_model",
                return_value=(mock_model, mock_processor),
            ),
            patch(
                "python_pkg.music_gen.music_generator.interactive_mode",
            ) as mock_inter,
        ):
            main()

        mock_inter.assert_called_once_with(mock_model, mock_processor)

    def test_dependencies_fail_exits(self) -> None:
        with (
            patch("sys.argv", ["music_generator", "test prompt"]),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=False,
            ),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_song_dependencies_fail_exits(self) -> None:
        with (
            patch(
                "sys.argv",
                ["music_generator", "--song", "la la"],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=False,
            ),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_speech_dependencies_fail_exits(self) -> None:
        with (
            patch(
                "sys.argv",
                ["music_generator", "--speech", "hello"],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=False,
            ),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_with_model_flag(self) -> None:
        mock_model = MagicMock()
        mock_processor = MagicMock()

        with (
            patch(
                "sys.argv",
                ["music_generator", "--model", "large", "epic orchestra"],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.select_model_size",
                return_value="large",
            ) as mock_select,
            patch(
                "python_pkg.music_gen.music_generator.load_model",
                return_value=(mock_model, mock_processor),
            ),
            patch("python_pkg.music_gen.music_generator.generate_music"),
        ):
            main()

        mock_select.assert_called_once_with("large")

    def test_with_duration_flag(self) -> None:
        mock_model = MagicMock()
        mock_processor = MagicMock()

        with (
            patch(
                "sys.argv",
                ["music_generator", "--duration", "30", "bass drop"],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.select_model_size",
                return_value="medium",
            ),
            patch(
                "python_pkg.music_gen.music_generator.load_model",
                return_value=(mock_model, mock_processor),
            ),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
            ) as mock_gen,
        ):
            main()

        mock_gen.assert_called_once_with(
            "bass drop",
            mock_model,
            mock_processor,
            duration_seconds=30,
            output_dir=None,
        )

    def test_with_output_flag(self) -> None:
        mock_model = MagicMock()
        mock_processor = MagicMock()

        with (
            patch(
                "sys.argv",
                ["music_generator", "--output", tempfile.gettempdir() + "/out", "test"],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.select_model_size",
                return_value="medium",
            ),
            patch(
                "python_pkg.music_gen.music_generator.load_model",
                return_value=(mock_model, mock_processor),
            ),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
            ) as mock_gen,
        ):
            main()

        _, kwargs = mock_gen.call_args
        assert kwargs["output_dir"] is not None

    def test_speech_with_voice_flag(self) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "music_generator",
                    "--speech",
                    "--voice",
                    "v2/en_speaker_3",
                    "Hello",
                ],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.generate_speech",
            ) as mock_speech,
        ):
            main()

        mock_speech.assert_called_once_with(
            "Hello",
            voice="v2/en_speaker_3",
            output_dir=None,
        )

    def test_song_with_voice_flag(self) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "music_generator",
                    "--song",
                    "--voice",
                    "v2/en_speaker_0",
                    "sing",
                ],
            ),
            patch(
                "python_pkg.music_gen.music_generator.check_dependencies",
                return_value=True,
            ),
            patch(
                "python_pkg.music_gen.music_generator.generate_song",
            ) as mock_song,
        ):
            main()

        mock_song.assert_called_once_with(
            "sing",
            "upbeat pop instrumental backing track",
            voice="v2/en_speaker_0",
            output_dir=None,
        )
