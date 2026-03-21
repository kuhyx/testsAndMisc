"""Tests for generate_song in python_pkg.music_gen._music_speech."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np

from python_pkg.music_gen._music_speech import generate_song

if TYPE_CHECKING:
    from pathlib import Path


class TestGenerateSong:
    """Tests for generate_song()."""

    def test_with_output_dir(self, tmp_path: Path) -> None:
        vocals = np.ones(24000, dtype=np.float32)
        instrumental = np.ones(3200, dtype=np.float32)
        resampled = np.ones(3200, dtype=np.float32)
        mixed = np.ones(3200, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_speech._generate_vocals_for_song",
                return_value=(vocals, 24000),
            ),
            patch(
                "python_pkg.music_gen._music_speech._generate_instrumental_for_song",
                return_value=(instrumental, 32000),
            ),
            patch(
                "python_pkg.music_gen._music_speech._resample_audio",
                return_value=resampled,
            ),
            patch(
                "python_pkg.music_gen._music_speech._mix_audio",
                return_value=mixed,
            ),
            patch("scipy.io.wavfile.write") as mock_write,
        ):
            result = generate_song(
                "la la la",
                "upbeat pop",
                output_dir=tmp_path,
            )

        assert result.parent == tmp_path
        assert result.suffix == ".wav"
        assert "song" in result.name
        mock_write.assert_called_once()

    def test_default_output_dir(self) -> None:
        vocals = np.ones(24000, dtype=np.float32)
        instrumental = np.ones(3200, dtype=np.float32)
        resampled = np.ones(3200, dtype=np.float32)
        mixed = np.ones(3200, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_speech._generate_vocals_for_song",
                return_value=(vocals, 24000),
            ),
            patch(
                "python_pkg.music_gen._music_speech._generate_instrumental_for_song",
                return_value=(instrumental, 32000),
            ),
            patch(
                "python_pkg.music_gen._music_speech._resample_audio",
                return_value=resampled,
            ),
            patch(
                "python_pkg.music_gen._music_speech._mix_audio",
                return_value=mixed,
            ),
            patch("scipy.io.wavfile.write"),
            patch("pathlib.Path.mkdir"),
        ):
            result = generate_song("la la la", "pop")

        assert "output" in str(result.parent)

    def test_lyrics_sanitization(self, tmp_path: Path) -> None:
        vocals = np.ones(24000, dtype=np.float32)
        instrumental = np.ones(3200, dtype=np.float32)
        resampled = np.ones(3200, dtype=np.float32)
        mixed = np.ones(3200, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_speech._generate_vocals_for_song",
                return_value=(vocals, 24000),
            ),
            patch(
                "python_pkg.music_gen._music_speech._generate_instrumental_for_song",
                return_value=(instrumental, 32000),
            ),
            patch(
                "python_pkg.music_gen._music_speech._resample_audio",
                return_value=resampled,
            ),
            patch(
                "python_pkg.music_gen._music_speech._mix_audio",
                return_value=mixed,
            ),
            patch("scipy.io.wavfile.write"),
        ):
            result = generate_song(
                "hello!@#$ world",
                "rock",
                output_dir=tmp_path,
            )

        assert "hello_world" in result.name

    def test_custom_voice(self, tmp_path: Path) -> None:
        vocals = np.ones(24000, dtype=np.float32)
        instrumental = np.ones(3200, dtype=np.float32)
        resampled = np.ones(3200, dtype=np.float32)
        mixed = np.ones(3200, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_speech._generate_vocals_for_song",
                return_value=(vocals, 24000),
            ) as mock_vocals,
            patch(
                "python_pkg.music_gen._music_speech._generate_instrumental_for_song",
                return_value=(instrumental, 32000),
            ),
            patch(
                "python_pkg.music_gen._music_speech._resample_audio",
                return_value=resampled,
            ),
            patch(
                "python_pkg.music_gen._music_speech._mix_audio",
                return_value=mixed,
            ),
            patch("scipy.io.wavfile.write"),
        ):
            generate_song(
                "test",
                "jazz",
                voice="v2/en_speaker_3",
                output_dir=tmp_path,
            )

        mock_vocals.assert_called_once_with("test", "v2/en_speaker_3")
