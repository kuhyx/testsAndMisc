"""Tests for python_pkg.music_gen._music_generation module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from python_pkg.music_gen._music_generation import (
    SEGMENT_DURATION,
    VRAM_THRESHOLD_LARGE,
    VRAM_THRESHOLD_MEDIUM,
    _calculate_segment_duration,
    _generate_long_audio,
    crossfade_audio,
    generate_segment,
    get_device,
    get_vram_gb,
    load_model,
    select_model_size,
)


class TestGetDevice:
    """Tests for get_device()."""

    def test_nvidia_gpu_with_cuda(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "RTX 3080"
        props = MagicMock()
        props.total_memory = 12 * 1024**3
        mock_torch.cuda.get_device_properties.return_value = props
        mock_torch.backends.mps.is_available.return_value = False

        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch.dict("sys.modules", {"torch": mock_torch}),
            patch("shutil.which", return_value="/usr/bin/nvidia-smi"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = get_device()

        assert result == "cuda"

    def test_nvidia_gpu_without_cuda_raises(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch.dict("sys.modules", {"torch": mock_torch}),
            patch("shutil.which", return_value="/usr/bin/nvidia-smi"),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(RuntimeError, match="NVIDIA GPU detected"):
                get_device()

    def test_nvidia_smi_not_found(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        # hasattr check: torch.backends has 'mps' attr
        mock_backends = MagicMock()
        mock_backends.mps.is_available.return_value = False
        mock_torch.backends = mock_backends

        with (
            patch.dict("sys.modules", {"torch": mock_torch}),
            patch("shutil.which", return_value=None),
        ):
            result = get_device()

        assert result == "cpu"

    def test_nvidia_smi_returns_nonzero(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_backends = MagicMock()
        mock_backends.mps.is_available.return_value = False
        mock_torch.backends = mock_backends

        mock_result = MagicMock()
        mock_result.returncode = 1

        with (
            patch.dict("sys.modules", {"torch": mock_torch}),
            patch("shutil.which", return_value="/usr/bin/nvidia-smi"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = get_device()

        assert result == "cpu"

    def test_mps_device(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_backends = MagicMock()
        mock_backends.mps.is_available.return_value = True
        mock_torch.backends = mock_backends

        with (
            patch.dict("sys.modules", {"torch": mock_torch}),
            patch("shutil.which", return_value=None),
        ):
            result = get_device()

        assert result == "mps"

    def test_file_not_found_error(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_backends = MagicMock()
        mock_backends.mps.is_available.return_value = False
        mock_torch.backends = mock_backends

        with (
            patch.dict("sys.modules", {"torch": mock_torch}),
            patch("shutil.which", side_effect=FileNotFoundError),
        ):
            result = get_device()

        assert result == "cpu"


class TestGetVramGb:
    """Tests for get_vram_gb()."""

    def test_cuda_available(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        props = MagicMock()
        props.total_memory = 8 * 1024**3
        mock_torch.cuda.get_device_properties.return_value = props

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = get_vram_gb()

        assert result == pytest.approx(8.0)

    def test_no_cuda(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = get_vram_gb()

        assert result is None


class TestSelectModelSize:
    """Tests for select_model_size()."""

    def test_user_choice_provided(self) -> None:
        assert select_model_size("small") == "small"

    def test_no_gpu_returns_medium(self) -> None:
        with patch(
            "python_pkg.music_gen._music_generation.get_vram_gb",
            return_value=None,
        ):
            assert select_model_size() == "medium"

    def test_large_vram(self) -> None:
        with patch(
            "python_pkg.music_gen._music_generation.get_vram_gb",
            return_value=VRAM_THRESHOLD_LARGE,
        ):
            assert select_model_size() == "large"

    def test_medium_vram(self) -> None:
        with patch(
            "python_pkg.music_gen._music_generation.get_vram_gb",
            return_value=VRAM_THRESHOLD_MEDIUM,
        ):
            assert select_model_size() == "medium"

    def test_small_vram(self) -> None:
        with patch(
            "python_pkg.music_gen._music_generation.get_vram_gb",
            return_value=4.0,
        ):
            assert select_model_size() == "small"


class TestLoadModel:
    """Tests for load_model()."""

    def test_load_model(self) -> None:
        mock_processor = MagicMock()
        mock_model = MagicMock()
        mock_model.to.return_value = mock_model

        mock_auto_processor = MagicMock()
        mock_auto_processor.from_pretrained.return_value = mock_processor
        mock_musicgen = MagicMock()
        mock_musicgen.from_pretrained.return_value = mock_model

        with (
            patch(
                "python_pkg.music_gen._music_generation.get_device",
                return_value="cpu",
            ),
            patch.dict(
                "sys.modules",
                {"transformers": MagicMock()},
            ),
            patch(
                "python_pkg.music_gen._music_generation.AutoProcessor",
                mock_auto_processor,
                create=True,
            ),
            patch(
                "python_pkg.music_gen._music_generation.MusicgenForConditionalGeneration",
                mock_musicgen,
                create=True,
            ),
        ):
            # We need to mock the imports inside load_model
            pass

        # Alternative approach - mock at the transformers import level
        mock_transformers = MagicMock()
        mock_transformers.AutoProcessor.from_pretrained.return_value = mock_processor
        mock_from_pretrained = (
            mock_transformers.MusicgenForConditionalGeneration.from_pretrained
        )
        mock_from_pretrained.return_value = mock_model

        with (
            patch(
                "python_pkg.music_gen._music_generation.get_device",
                return_value="cpu",
            ),
            patch.dict("sys.modules", {"transformers": mock_transformers}),
        ):
            model, processor = load_model("small")

        assert model == mock_model
        assert processor == mock_processor
        mock_model.to.assert_called_once_with("cpu")


class TestCrossfadeAudio:
    """Tests for crossfade_audio()."""

    def test_zero_crossfade_samples(self) -> None:
        a1 = np.array([1.0, 2.0, 3.0])
        a2 = np.array([4.0, 5.0, 6.0])
        result = crossfade_audio(a1, a2, 0)
        np.testing.assert_array_equal(result, np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))

    def test_negative_crossfade_samples(self) -> None:
        a1 = np.array([1.0, 2.0])
        a2 = np.array([3.0, 4.0])
        result = crossfade_audio(a1, a2, -1)
        np.testing.assert_array_equal(result, np.array([1.0, 2.0, 3.0, 4.0]))

    def test_crossfade_larger_than_audio1(self) -> None:
        a1 = np.array([1.0, 2.0])
        a2 = np.array([3.0, 4.0, 5.0])
        result = crossfade_audio(a1, a2, 5)
        np.testing.assert_array_equal(result, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))

    def test_normal_crossfade(self) -> None:
        a1 = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float64)
        a2 = np.array([2.0, 2.0, 2.0, 2.0], dtype=np.float64)
        result = crossfade_audio(a1, a2, 2)
        assert len(result) == 6
        # First 2 samples from a1 (non-crossfaded)
        assert result[0] == 1.0
        assert result[1] == 1.0
        # Last 2 samples from a2 (non-crossfaded)
        assert result[4] == 2.0
        assert result[5] == 2.0


class TestGenerateSegment:
    """Tests for generate_segment()."""

    def test_generate_segment(self) -> None:
        mock_torch = MagicMock()
        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        mock_processor = MagicMock()
        mock_processor.return_value = {"input_ids": MagicMock()}

        mock_model = MagicMock()
        audio_tensor = MagicMock()
        audio_tensor.cpu.return_value.numpy.return_value = np.array([0.1, 0.2])
        # audio_values[0, 0] needs to work with tuple indexing
        audio_values = MagicMock()
        audio_values.__getitem__ = MagicMock(return_value=audio_tensor)
        mock_model.generate.return_value = audio_values

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = generate_segment("test", mock_model, mock_processor, 10, "cpu")

        np.testing.assert_array_equal(result, np.array([0.1, 0.2]))


class TestCalculateSegmentDuration:
    """Tests for _calculate_segment_duration()."""

    def test_non_last_segment(self) -> None:
        result = _calculate_segment_duration(0, 3, 0, 32000, 60)
        assert result == SEGMENT_DURATION

    def test_last_segment_remaining_large(self) -> None:
        # Last segment with a lot of remaining time
        result = _calculate_segment_duration(2, 3, 32000 * 40, 32000, 60)
        # remaining = 60 - 40 = 20
        # min_duration = max(5, 20 + 2) = 22
        # min(25, 22) = 22
        assert result == 22

    def test_last_segment_remaining_small(self) -> None:
        # Last segment with very little remaining
        result = _calculate_segment_duration(2, 3, 32000 * 58, 32000, 60)
        # remaining = 60 - 58 = 2
        # min_duration = max(5, 2 + 2) = 5
        # min(25, 5) = 5
        assert result == 5


class TestGenerateLongAudio:
    """Tests for _generate_long_audio()."""

    def test_generate_long_audio(self) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 100

        mock_processor = MagicMock()

        segment = np.ones(100 * SEGMENT_DURATION, dtype=np.float32)

        with patch(
            "python_pkg.music_gen._music_generation.generate_segment",
            return_value=segment,
        ):
            result = _generate_long_audio("test", mock_model, mock_processor, 60)

        assert isinstance(result, np.ndarray)

    def test_generate_long_audio_no_trim(self) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 10

        mock_processor = MagicMock()

        # Return a small segment so total < target, no trimming occurs
        segment = np.ones(10 * 5, dtype=np.float32)

        with patch(
            "python_pkg.music_gen._music_generation.generate_segment",
            return_value=segment,
        ):
            result = _generate_long_audio("test", mock_model, mock_processor, 200)

        # Result should not exceed 200 * 10 = 2000 samples
        assert isinstance(result, np.ndarray)

    def test_generate_long_audio_trims(self) -> None:
        mock_model = MagicMock()
        mock_param = MagicMock()
        mock_param.device = "cpu"
        mock_model.parameters.return_value = iter([mock_param])
        mock_model.config.audio_encoder.sampling_rate = 10

        mock_processor = MagicMock()

        # Return large segment each time so result exceeds target
        segment = np.ones(10 * SEGMENT_DURATION, dtype=np.float32)

        with patch(
            "python_pkg.music_gen._music_generation.generate_segment",
            return_value=segment,
        ):
            result = _generate_long_audio("test", mock_model, mock_processor, 30)

        # Should be trimmed to exactly 30 * 10 = 300 samples
        assert len(result) == 300
