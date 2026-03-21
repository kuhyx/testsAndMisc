"""Tests for python_pkg.music_gen._music_speech module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from python_pkg.music_gen._music_speech import (
    BARK_MAX_CHARS,
    _generate_instrumental_for_song,
    _generate_vocals_for_song,
    _mix_audio,
    _resample_audio,
    _split_into_sentences,
    generate_speech,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestSplitIntoSentences:
    """Tests for _split_into_sentences()."""

    def test_single_sentence(self) -> None:
        result = _split_into_sentences("Hello world.")
        assert result == ["Hello world."]

    def test_multiple_sentences(self) -> None:
        result = _split_into_sentences("First sentence. Second sentence. Third.")
        assert len(result) >= 1
        # All sentences should be present
        combined = " ".join(result)
        assert "First sentence." in combined
        assert "Second sentence." in combined

    def test_short_sentences_grouped(self) -> None:
        result = _split_into_sentences("Hi. Ok. Yes.")
        # Short sentences should be grouped together (< BARK_MAX_CHARS)
        assert len(result) == 1

    def test_long_text_splits(self) -> None:
        # Create text that exceeds BARK_MAX_CHARS when combined
        long_sentence = "A" * (BARK_MAX_CHARS - 10) + "."
        text = f"{long_sentence} {long_sentence}"
        result = _split_into_sentences(text)
        assert len(result) >= 2

    def test_empty_result_returns_original(self) -> None:
        # A single word with no sentence boundaries
        result = _split_into_sentences("hello")
        assert result == ["hello"]

    def test_whitespace_stripped(self) -> None:
        result = _split_into_sentences("  Hello world.  ")
        assert result[0] == "Hello world."

    def test_current_empty_in_else_branch(self) -> None:
        # First sentence exceeds BARK_MAX_CHARS so current is empty when else hit
        long_sent = "A" * (BARK_MAX_CHARS + 10) + "."
        short_sent = "Short."
        text = f"{long_sent} {short_sent}"
        result = _split_into_sentences(text)
        assert len(result) >= 2

    def test_all_sentences_too_long(self) -> None:
        # Each individual sentence is huge -- current is never empty at else
        s1 = "A" * (BARK_MAX_CHARS + 10) + "."
        s2 = "B" * (BARK_MAX_CHARS + 10) + "."
        text = f"{s1} {s2}"
        result = _split_into_sentences(text)
        assert len(result) >= 2

    def test_empty_string_input(self) -> None:
        # Empty string → sentences=[''], current stays '' after loop
        result = _split_into_sentences("")
        assert result == [""]


class TestResampleAudio:
    """Tests for _resample_audio()."""

    def test_same_rate_returns_unchanged(self) -> None:
        audio = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = _resample_audio(audio, 44100, 44100)
        np.testing.assert_array_equal(result, audio)

    def test_resample_different_rate(self) -> None:
        audio = np.ones(100, dtype=np.float32)
        result = _resample_audio(audio, 44100, 22050)
        # Should be shorter since target rate is lower
        expected_length = int(len(audio) / 44100 * 22050)
        assert len(result) == expected_length
        assert result.dtype == np.float32


class TestMixAudio:
    """Tests for _mix_audio()."""

    def test_vocals_shorter_than_instrumental(self) -> None:
        instrumental = np.ones(100, dtype=np.float32)
        vocals = np.ones(50, dtype=np.float32)
        result = _mix_audio(instrumental, vocals)
        assert len(result) == 100

    def test_vocals_longer_than_instrumental(self) -> None:
        instrumental = np.ones(50, dtype=np.float32)
        vocals = np.ones(100, dtype=np.float32)
        result = _mix_audio(instrumental, vocals)
        assert len(result) == 50

    def test_same_length(self) -> None:
        instrumental = np.ones(100, dtype=np.float32)
        vocals = np.ones(100, dtype=np.float32)
        result = _mix_audio(instrumental, vocals)
        assert len(result) == 100

    def test_normalization_when_clipping(self) -> None:
        instrumental = np.ones(10, dtype=np.float32) * 2.0
        vocals = np.ones(10, dtype=np.float32) * 2.0
        result = _mix_audio(
            instrumental, vocals, vocal_volume=1.0, instrumental_volume=1.0
        )
        # Should be normalized so max <= 1.0
        assert np.max(np.abs(result)) <= 1.0 + 1e-6

    def test_no_normalization_needed(self) -> None:
        instrumental = np.ones(10, dtype=np.float32) * 0.1
        vocals = np.ones(10, dtype=np.float32) * 0.1
        result = _mix_audio(
            instrumental, vocals, vocal_volume=0.5, instrumental_volume=0.5
        )
        assert result.dtype == np.float32

    def test_output_type(self) -> None:
        instrumental = np.ones(10, dtype=np.float32) * 0.5
        vocals = np.ones(10, dtype=np.float32) * 0.5
        result = _mix_audio(instrumental, vocals)
        assert result.dtype == np.float32


class TestGenerateSpeech:
    """Tests for generate_speech()."""

    def test_single_sentence(self, tmp_path: Path) -> None:
        mock_torch = MagicMock()
        mock_bark = MagicMock()
        mock_bark.SAMPLE_RATE = 24000
        mock_bark.generate_audio.return_value = np.zeros(24000, dtype=np.float32)

        np.zeros(24000, dtype=np.float32)

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "scipy": MagicMock(),
                    "scipy.io": MagicMock(),
                    "scipy.io.wavfile": MagicMock(),
                    "bark": mock_bark,
                },
            ),
            patch(
                "python_pkg.music_gen._music_speech._split_into_sentences",
                return_value=["Hello world."],
            ),
            patch("scipy.io.wavfile.write"),
        ):
            result = generate_speech("Hello world.", output_dir=tmp_path)

        assert result.parent == tmp_path
        assert result.suffix == ".wav"
        assert "speech" in result.name

    def test_multiple_sentences(self, tmp_path: Path) -> None:
        mock_torch = MagicMock()
        mock_bark = MagicMock()
        mock_bark.SAMPLE_RATE = 24000
        mock_bark.generate_audio.return_value = np.zeros(24000, dtype=np.float32)

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "scipy": MagicMock(),
                    "scipy.io": MagicMock(),
                    "scipy.io.wavfile": MagicMock(),
                    "bark": mock_bark,
                },
            ),
            patch(
                "python_pkg.music_gen._music_speech._split_into_sentences",
                return_value=["First sentence.", "Second sentence."],
            ),
            patch("scipy.io.wavfile.write"),
        ):
            result = generate_speech(
                "First sentence. Second sentence.",
                output_dir=tmp_path,
            )

        assert result.suffix == ".wav"

    def test_default_output_dir(self) -> None:
        mock_torch = MagicMock()
        mock_bark = MagicMock()
        mock_bark.SAMPLE_RATE = 24000
        mock_bark.generate_audio.return_value = np.zeros(24000, dtype=np.float32)

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "scipy": MagicMock(),
                    "scipy.io": MagicMock(),
                    "scipy.io.wavfile": MagicMock(),
                    "bark": mock_bark,
                },
            ),
            patch(
                "python_pkg.music_gen._music_speech._split_into_sentences",
                return_value=["Hello."],
            ),
            patch("scipy.io.wavfile.write"),
            patch("pathlib.Path.mkdir"),
        ):
            result = generate_speech("Hello.")

        assert "output" in str(result.parent)

    def test_patched_load_called(self, tmp_path: Path) -> None:
        """Ensure the patched_load inner function is actually invoked."""
        import sys

        mock_torch = MagicMock()
        original_load = MagicMock(return_value="loaded")
        mock_torch.load = original_load

        mock_bark = MagicMock()
        mock_bark.SAMPLE_RATE = 24000
        mock_bark.generate_audio.return_value = np.zeros(24000, dtype=np.float32)

        # Make preload_models call torch.load so patched_load runs
        def call_torch_load() -> None:
            sys.modules["torch"].load("model.pt")

        mock_bark.preload_models.side_effect = call_torch_load

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "scipy": MagicMock(),
                    "scipy.io": MagicMock(),
                    "scipy.io.wavfile": MagicMock(),
                    "bark": mock_bark,
                },
            ),
            patch(
                "python_pkg.music_gen._music_speech._split_into_sentences",
                return_value=["Hello."],
            ),
            patch("scipy.io.wavfile.write"),
        ):
            generate_speech("Hello.", output_dir=tmp_path)

        # The original_load should have been called via patched_load
        original_load.assert_called_once_with("model.pt", weights_only=False)

    def test_torch_load_restored_after_exception(self) -> None:
        mock_torch = MagicMock()
        original_load = mock_torch.load

        mock_bark = MagicMock()
        mock_bark.preload_models.side_effect = RuntimeError("test error")

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "scipy": MagicMock(),
                    "scipy.io": MagicMock(),
                    "scipy.io.wavfile": MagicMock(),
                    "bark": mock_bark,
                },
            ),
            pytest.raises(RuntimeError, match="test error"),
        ):
            generate_speech("Hello.")

        # torch.load should be restored
        assert mock_torch.load == original_load


class TestGenerateVocalsForSong:
    """Tests for _generate_vocals_for_song()."""

    def test_single_sentence(self) -> None:
        mock_torch = MagicMock()
        mock_bark = MagicMock()
        mock_bark.SAMPLE_RATE = 24000
        audio_array = np.zeros(24000, dtype=np.float32)
        mock_bark.generate_audio.return_value = audio_array

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "bark": mock_bark,
                },
            ),
            patch(
                "python_pkg.music_gen._music_speech._split_into_sentences",
                return_value=["Hello."],
            ),
        ):
            vocals, sr = _generate_vocals_for_song("Hello.", "v2/en_speaker_6")

        assert sr == 24000
        np.testing.assert_array_equal(vocals, audio_array)

    def test_multiple_sentences(self) -> None:
        mock_torch = MagicMock()
        mock_bark = MagicMock()
        mock_bark.SAMPLE_RATE = 24000
        audio_array = np.ones(12000, dtype=np.float32)
        mock_bark.generate_audio.return_value = audio_array

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "bark": mock_bark,
                },
            ),
            patch(
                "python_pkg.music_gen._music_speech._split_into_sentences",
                return_value=["First.", "Second."],
            ),
        ):
            vocals, sr = _generate_vocals_for_song(
                "First. Second.",
                "v2/en_speaker_6",
            )

        assert sr == 24000
        assert len(vocals) == 24000  # Two 12000-sample arrays concatenated

    def test_torch_load_restored(self) -> None:
        mock_torch = MagicMock()
        original_load = mock_torch.load

        mock_bark = MagicMock()
        mock_bark.preload_models.side_effect = RuntimeError("fail")

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "bark": mock_bark,
                },
            ),
            pytest.raises(RuntimeError, match="fail"),
        ):
            _generate_vocals_for_song("Hello.", "v2/en_speaker_6")

        assert mock_torch.load == original_load

    def test_patched_load_is_invoked(self) -> None:
        """Ensure patched_load inner function runs in _generate_vocals_for_song."""
        import sys

        mock_torch = MagicMock()
        original_load = MagicMock(return_value="loaded_model")
        mock_torch.load = original_load

        mock_bark = MagicMock()
        mock_bark.SAMPLE_RATE = 24000
        audio_array = np.zeros(24000, dtype=np.float32)
        mock_bark.generate_audio.return_value = audio_array

        def call_torch_load() -> None:
            sys.modules["torch"].load("weights.pt")

        mock_bark.preload_models.side_effect = call_torch_load

        with (
            patch.dict(
                "sys.modules",
                {
                    "torch": mock_torch,
                    "functools": __import__("functools"),
                    "numpy": np,
                    "bark": mock_bark,
                },
            ),
            patch(
                "python_pkg.music_gen._music_speech._split_into_sentences",
                return_value=["Hello."],
            ),
        ):
            vocals, sr = _generate_vocals_for_song("Hello.", "v2/en_speaker_6")

        assert sr == 24000
        # The original_load should have been called via patched_load
        original_load.assert_called_once_with("weights.pt", weights_only=False)


class TestGenerateInstrumentalForSong:
    """Tests for _generate_instrumental_for_song()."""

    def test_short_duration(self) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 100

        audio = np.zeros(100 * 10, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_speech.select_model_size",
                return_value="small",
            ),
            patch(
                "python_pkg.music_gen._music_speech.load_model",
                return_value=(mock_model, MagicMock()),
            ),
            patch(
                "python_pkg.music_gen._music_speech.generate_segment",
                return_value=audio,
            ),
        ):
            instrumental, sr = _generate_instrumental_for_song("test", 10)

        assert sr == 100
        np.testing.assert_array_equal(instrumental, audio)

    def test_long_duration(self) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 100

        audio = np.zeros(100 * 60, dtype=np.float32)

        with (
            patch(
                "python_pkg.music_gen._music_speech.select_model_size",
                return_value="small",
            ),
            patch(
                "python_pkg.music_gen._music_speech.load_model",
                return_value=(mock_model, MagicMock()),
            ),
            patch(
                "python_pkg.music_gen._music_speech._generate_long_audio",
                return_value=audio,
            ),
        ):
            instrumental, sr = _generate_instrumental_for_song("test", 60)

        assert sr == 100
