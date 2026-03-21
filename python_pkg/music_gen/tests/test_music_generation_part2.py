"""Tests for generate_music in python_pkg.music_gen._music_generation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np

from python_pkg.music_gen._music_generation import (
    SEGMENT_DURATION,
    generate_music,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestGenerateMusic:
    """Tests for generate_music()."""

    def test_short_duration_with_output_dir(self, tmp_path: Path) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 100

        mock_processor = MagicMock()
        audio = np.ones(100 * 10, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_generation.generate_segment",
                return_value=audio,
            ),
            patch("scipy.io.wavfile.write") as mock_write,
        ):
            result = generate_music(
                "test prompt",
                mock_model,
                mock_processor,
                duration_seconds=10,
                output_dir=tmp_path,
            )

        assert result.parent == tmp_path
        assert result.suffix == ".wav"
        assert "test_prompt" in result.name
        mock_write.assert_called_once()

    def test_long_duration_uses_long_audio(self, tmp_path: Path) -> None:
        mock_model = MagicMock()
        mock_model.config.audio_encoder.sampling_rate = 100

        mock_processor = MagicMock()
        audio = np.ones(100 * 60, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_generation._generate_long_audio",
                return_value=audio,
            ),
            patch("scipy.io.wavfile.write"),
        ):
            result = generate_music(
                "long prompt",
                mock_model,
                mock_processor,
                duration_seconds=SEGMENT_DURATION + 1,
                output_dir=tmp_path,
            )

        assert result.suffix == ".wav"

    def test_default_output_dir(self) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 100

        mock_processor = MagicMock()
        audio = np.ones(100 * 5, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_generation.generate_segment",
                return_value=audio,
            ),
            patch("scipy.io.wavfile.write"),
            patch("pathlib.Path.mkdir"),
        ):
            result = generate_music(
                "test",
                mock_model,
                mock_processor,
                duration_seconds=5,
            )

        assert "output" in str(result.parent)

    def test_prompt_sanitization_special_chars(self, tmp_path: Path) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 100

        mock_processor = MagicMock()
        audio = np.ones(100 * 5, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_generation.generate_segment",
                return_value=audio,
            ),
            patch("scipy.io.wavfile.write"),
        ):
            result = generate_music(
                "hello!@#$%^&*() world",
                mock_model,
                mock_processor,
                duration_seconds=5,
                output_dir=tmp_path,
            )

        # Special chars stripped, spaces become underscores
        assert "hello_world" in result.name

    def test_exact_segment_duration(self, tmp_path: Path) -> None:
        """Duration == SEGMENT_DURATION should use short path."""
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 100

        mock_processor = MagicMock()
        audio = np.ones(100 * SEGMENT_DURATION, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_generation.generate_segment",
                return_value=audio,
            ) as mock_seg,
            patch("scipy.io.wavfile.write"),
        ):
            generate_music(
                "test",
                mock_model,
                mock_processor,
                duration_seconds=SEGMENT_DURATION,
                output_dir=tmp_path,
            )

        mock_seg.assert_called_once()
