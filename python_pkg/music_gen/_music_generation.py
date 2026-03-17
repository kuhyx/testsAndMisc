"""Core MusicGen model loading, device selection, and audio generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# VRAM thresholds for model selection (in GB)
VRAM_THRESHOLD_LARGE = 12  # Use large model with 12GB+ VRAM
VRAM_THRESHOLD_MEDIUM = 8  # Use medium model with 8GB+ VRAM

# Generation settings for segmented long audio
SEGMENT_DURATION = 25  # Seconds per segment (under 30s MusicGen limit)
CROSSFADE_DURATION = 2  # Seconds of crossfade between segments


def get_device() -> str:
    """Get the best available device (CUDA or MPS). No CPU fallback for NVIDIA.

    Raises:
        RuntimeError: If NVIDIA GPU is detected but CUDA is not available.
    """
    import torch

    # Check for NVIDIA GPU first
    nvidia_gpu_present = False
    try:
        import shutil
        import subprocess

        nvidia_smi_path = shutil.which("nvidia-smi")
        if nvidia_smi_path:
            result = subprocess.run(
                [nvidia_smi_path],
                capture_output=True,
                text=True,
                check=False,
            )
            nvidia_gpu_present = result.returncode == 0
    except FileNotFoundError:
        pass

    if nvidia_gpu_present:
        if not torch.cuda.is_available():
            msg = (
                "NVIDIA GPU detected but CUDA is not available!\n"
                "Please install PyTorch with CUDA support:\n"
                "  pip install torch torchaudio --index-url "
                "https://download.pytorch.org/whl/cu121"
            )
            raise RuntimeError(msg)
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"Using CUDA GPU: {gpu_name} ({vram:.1f}GB VRAM)")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        print("Using Apple Silicon (MPS)")
    else:
        device = "cpu"
        print("Using CPU (this will be slow)")
    return device


def get_vram_gb() -> float | None:
    """Get available VRAM in GB. Returns None if no CUDA GPU."""
    import torch

    if torch.cuda.is_available():
        return torch.cuda.get_device_properties(0).total_memory / 1024**3
    return None


def select_model_size(user_choice: str | None = None) -> str:
    """Select model size based on user choice or available VRAM.

    Args:
        user_choice: User's explicit model choice, or None for auto-selection.

    Returns:
        Model size: 'small', 'medium', or 'large'
    """
    if user_choice is not None:
        return user_choice

    vram = get_vram_gb()

    if vram is None:
        # No GPU, use medium as a safe default
        print("No CUDA GPU detected, defaulting to medium model")
        return "medium"

    # Select based on VRAM:
    # - large: needs ~10GB VRAM (safe with 12GB+)
    # - medium: needs ~6GB VRAM (safe with 8GB+)
    # - small: needs ~3GB VRAM
    if vram >= VRAM_THRESHOLD_LARGE:
        selected = "large"
    elif vram >= VRAM_THRESHOLD_MEDIUM:
        selected = "medium"
    else:
        selected = "small"

    print(f"Auto-selected '{selected}' model based on {vram:.1f}GB VRAM")
    return selected


def load_model(
    model_size: str = "medium",
) -> tuple[Any, Any]:
    """Load the MusicGen model.

    Args:
        model_size: One of 'small', 'medium', or 'large'
                   - small: ~500MB, fastest, lower quality
                   - medium: ~3.3GB, good balance (recommended)
                   - large: ~6.5GB, best quality, needs more VRAM

    Returns:
        Tuple of (model, processor)
    """
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    model_name = f"facebook/musicgen-{model_size}"
    print(f"\nLoading MusicGen {model_size} model...")
    print("(First run will download the model, this may take a while)")

    device = get_device()

    processor = AutoProcessor.from_pretrained(model_name)
    # Use safetensors format to avoid torch.load security issues with older PyTorch
    model = MusicgenForConditionalGeneration.from_pretrained(
        model_name,
        use_safetensors=True,
    )
    model = model.to(device)

    print(f"Model loaded successfully on {device}!")
    return model, processor


def crossfade_audio(
    audio1: object,
    audio2: object,
    crossfade_samples: int,
) -> object:
    """Crossfade two audio segments together.

    Args:
        audio1: First audio segment (numpy array)
        audio2: Second audio segment (numpy array)
        crossfade_samples: Number of samples to use for crossfade

    Returns:
        Combined audio with crossfade applied (numpy array)
    """
    import numpy as np

    if crossfade_samples <= 0 or len(audio1) < crossfade_samples:
        return np.concatenate([audio1, audio2])

    # Create fade curves
    fade_out = np.linspace(1.0, 0.0, crossfade_samples)
    fade_in = np.linspace(0.0, 1.0, crossfade_samples)

    # Apply fades
    audio1_end = audio1[-crossfade_samples:] * fade_out
    audio2_start = audio2[:crossfade_samples] * fade_in

    # Combine
    crossfaded = audio1_end + audio2_start

    # Build final audio
    return np.concatenate(
        [
            audio1[:-crossfade_samples],
            crossfaded,
            audio2[crossfade_samples:],
        ]
    )


def generate_segment(
    prompt: str,
    model: object,
    processor: object,
    duration_seconds: int,
    device: str,
) -> object:
    """Generate a single audio segment.

    Args:
        prompt: Text description of the music
        model: The MusicGen model
        processor: The MusicGen processor
        duration_seconds: Length of segment to generate
        device: Device to generate on

    Returns:
        Audio data as numpy array
    """
    import torch

    inputs = processor(
        text=[prompt],
        padding=True,
        return_tensors="pt",
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    max_new_tokens = int(duration_seconds * 50)

    with torch.no_grad():
        audio_values = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
        )

    return audio_values[0, 0].cpu().numpy()


def _calculate_segment_duration(
    segment_index: int,
    num_segments: int,
    generated_samples: int,
    sample_rate: int,
    total_duration: int,
) -> int:
    """Calculate duration for a specific segment.

    Args:
        segment_index: Current segment index
        num_segments: Total number of segments
        generated_samples: Number of samples generated so far
        sample_rate: Audio sample rate
        total_duration: Target total duration

    Returns:
        Duration in seconds for this segment
    """
    if segment_index == num_segments - 1:
        # Last segment: calculate remaining time
        generated_so_far = generated_samples / sample_rate
        remaining = total_duration - generated_so_far
        min_duration = max(5, int(remaining) + CROSSFADE_DURATION)
        return min(SEGMENT_DURATION, min_duration)
    return SEGMENT_DURATION


def _generate_long_audio(
    prompt: str,
    model: object,
    processor: object,
    duration_seconds: int,
) -> object:
    """Generate long audio by segmenting with crossfades.

    Args:
        prompt: Text description of the music
        model: The MusicGen model
        processor: The MusicGen processor
        duration_seconds: Total duration to generate

    Returns:
        Audio data as numpy array
    """
    import numpy as np

    device = str(next(model.parameters()).device)
    sample_rate = model.config.audio_encoder.sampling_rate
    crossfade_samples = CROSSFADE_DURATION * sample_rate

    effective_segment = SEGMENT_DURATION - CROSSFADE_DURATION
    total = duration_seconds + effective_segment - 1
    num_segments = max(1, total // effective_segment)

    print(f"Generating {num_segments} segments of ~{SEGMENT_DURATION}s each...")

    audio_data = np.array([], dtype=np.float32)

    for i in range(num_segments):
        segment_duration = _calculate_segment_duration(
            i,
            num_segments,
            len(audio_data),
            sample_rate,
            duration_seconds,
        )

        seg_num = i + 1
        msg = f"  Segment {seg_num}/{num_segments} ({segment_duration}s)..."
        print(msg, end=" ", flush=True)

        segment = generate_segment(
            prompt,
            model,
            processor,
            segment_duration,
            device,
        )

        if len(audio_data) == 0:
            audio_data = segment
        else:
            audio_data = crossfade_audio(audio_data, segment, crossfade_samples)

        print(f"done (total: {len(audio_data) / sample_rate:.1f}s)")

    # Trim to exact duration if needed
    target_samples = int(duration_seconds * sample_rate)
    if len(audio_data) > target_samples:
        audio_data = audio_data[:target_samples]

    return audio_data


def generate_music(
    prompt: str,
    model: object,
    processor: object,
    duration_seconds: int = 10,
    output_dir: Path | None = None,
) -> Path:
    """Generate music from a text prompt.

    For durations over 30 seconds, generates in segments with crossfading.

    Args:
        prompt: Text description of the music to generate
        model: The MusicGen model
        processor: The MusicGen processor
        duration_seconds: Length of audio to generate (any duration supported)
        output_dir: Directory to save output (defaults to ./output)

    Returns:
        Path to the generated audio file
    """
    import scipy.io.wavfile

    if output_dir is None:
        output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    sample_rate = model.config.audio_encoder.sampling_rate

    # For short durations, generate directly
    if duration_seconds <= SEGMENT_DURATION:
        print(f"\nGenerating {duration_seconds}s of music...")
        print(f"Prompt: {prompt!r}")
        device = str(next(model.parameters()).device)
        audio_data = generate_segment(
            prompt,
            model,
            processor,
            duration_seconds,
            device,
        )
    else:
        # Long duration: generate in segments with crossfading
        print(f"\nGenerating {duration_seconds}s of music in segments...")
        print(f"Prompt: {prompt!r}")
        audio_data = _generate_long_audio(prompt, model, processor, duration_seconds)

    # Create filename with timestamp and sanitized prompt
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_prompt = "".join(c if c.isalnum() or c in " -_" else "" for c in prompt[:30])
    safe_prompt = safe_prompt.strip().replace(" ", "_")
    filename = f"{timestamp}_{safe_prompt}.wav"
    output_path = output_dir / filename

    scipy.io.wavfile.write(output_path, sample_rate, audio_data)

    print(f"\nSaved to: {output_path}")
    print(f"Duration: {len(audio_data) / sample_rate:.1f}s")

    return output_path
