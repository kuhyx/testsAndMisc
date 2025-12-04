#!/usr/bin/env python3
"""Local AI music generator using Meta's MusicGen.

Generates music from text prompts using the open-source MusicGen model.
First run will download the model (~3.3GB for medium, ~500MB for small).

Usage:
    python music_generator.py "upbeat electronic dance music with synths"
    python music_generator.py --duration 15 "calm acoustic guitar melody"
    python music_generator.py --model small "jazz piano solo"
    python music_generator.py --interactive  # Interactive mode
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# VRAM thresholds for model selection (in GB)
VRAM_THRESHOLD_LARGE = 12  # Use large model with 12GB+ VRAM
VRAM_THRESHOLD_MEDIUM = 8  # Use medium model with 8GB+ VRAM

# Generation settings for segmented long audio
SEGMENT_DURATION = 25  # Seconds per segment (under 30s MusicGen limit)
CROSSFADE_DURATION = 2  # Seconds of crossfade between segments
BARK_MAX_CHARS = 200  # Max characters per Bark segment (~13s of speech)


def check_dependencies(*, include_bark: bool = False) -> bool:
    """Check if required packages are installed.

    Args:
        include_bark: Whether to check for Bark dependencies as well.
    """
    missing = []

    try:
        import torch  # noqa: F401
    except ImportError:
        missing.append("torch")

    try:
        import transformers  # noqa: F401
    except ImportError:
        missing.append("transformers")

    try:
        import scipy  # noqa: F401
    except ImportError:
        missing.append("scipy")

    if include_bark:
        try:
            from bark import generate_audio as _bark_gen  # noqa: F401
        except ImportError:
            missing.append("git+https://github.com/suno-ai/bark.git")

    if missing:
        print("Missing dependencies. Install with:")
        print(f"  pip install {' '.join(missing)}")
        print("\nFor CUDA support:")
        print("  pip install torch --index-url https://download.pytorch.org/whl/cu121")
        print("  pip install transformers scipy")
        if include_bark:
            print("\nFor Bark vocals:")
            print("  pip install git+https://github.com/suno-ai/bark.git")
        return False
    return True


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
) -> tuple:  # type: ignore[type-arg]
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


# Available Bark voice presets
BARK_VOICES = [
    "v2/en_speaker_0",
    "v2/en_speaker_1",
    "v2/en_speaker_2",
    "v2/en_speaker_3",
    "v2/en_speaker_4",
    "v2/en_speaker_5",
    "v2/en_speaker_6",
    "v2/en_speaker_7",
    "v2/en_speaker_8",
    "v2/en_speaker_9",
]


def generate_speech(
    text: str,
    voice: str = "v2/en_speaker_6",
    output_dir: Path | None = None,
) -> Path:
    """Generate speech audio from text using Bark.

    Bark supports various speech patterns:
        - [laughter], [laughs], [sighs], [music]
        - [gasps], [clears throat], — or ... for hesitations
        - ♪ for singing

    Args:
        text: Text to convert to speech (max ~13s per segment)
        voice: Voice preset to use (see BARK_VOICES)
        output_dir: Directory to save output (defaults to ./output)

    Returns:
        Path to the generated audio file
    """
    import functools

    import numpy as np
    import scipy.io.wavfile
    import torch

    # Bark uses older checkpoint format with pickle
    # Monkey-patch torch.load to allow unsafe loading for Bark models
    original_torch_load = torch.load

    @functools.wraps(original_torch_load)
    def patched_load(*args: object, **kwargs: object) -> object:
        kwargs.setdefault("weights_only", False)
        return original_torch_load(*args, **kwargs)

    torch.load = patched_load

    try:
        from bark import SAMPLE_RATE, generate_audio, preload_models

        if output_dir is None:
            output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)

        print("\nLoading Bark model...")
        print("(First run will download models, ~5GB total)")
        preload_models()

        print(f"\nGenerating speech with voice: {voice}")
        print(f"Text: {text!r}")

        # Bark can only generate ~13s at a time
        # For longer text, we need to split into sentences
        audio_segments = []

        # Split on sentence boundaries for longer texts
        sentences = _split_into_sentences(text)

        for i, sentence in enumerate(sentences):
            if len(sentences) > 1:
                print(f"  Generating segment {i + 1}/{len(sentences)}...")

            audio = generate_audio(
                sentence.strip(),
                history_prompt=voice,
            )
            audio_segments.append(audio)

        # Combine segments
        if len(audio_segments) > 1:
            audio_data = np.concatenate(audio_segments)
        else:
            audio_data = audio_segments[0]

        # Create filename
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_text = "".join(c if c.isalnum() or c in " -_" else "" for c in text[:30])
        safe_text = safe_text.strip().replace(" ", "_")
        filename = f"{timestamp}_speech_{safe_text}.wav"
        output_path = output_dir / filename

        scipy.io.wavfile.write(output_path, SAMPLE_RATE, audio_data)

        print(f"\nSaved to: {output_path}")
        print(f"Duration: {len(audio_data) / SAMPLE_RATE:.1f}s")

        return output_path
    finally:
        # Restore original torch.load
        torch.load = original_torch_load


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for Bark processing.

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    import re

    # Split on sentence-ending punctuation followed by space
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    # Group very short sentences together
    result = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) < BARK_MAX_CHARS:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                result.append(current)
            current = sentence
    if current:
        result.append(current)

    return result if result else [text]


def _resample_audio(
    audio: object,
    orig_sr: int,
    target_sr: int,
) -> object:
    """Resample audio to a different sample rate.

    Args:
        audio: Audio data as numpy array
        orig_sr: Original sample rate
        target_sr: Target sample rate

    Returns:
        Resampled audio data
    """
    import numpy as np
    from scipy import signal

    if orig_sr == target_sr:
        return audio

    # Calculate the resampling ratio
    duration = len(audio) / orig_sr
    target_length = int(duration * target_sr)

    return signal.resample(audio, target_length).astype(np.float32)


def _mix_audio(
    instrumental: object,
    vocals: object,
    vocal_volume: float = 0.8,
    instrumental_volume: float = 0.6,
) -> object:
    """Mix vocals over instrumental track.

    Args:
        instrumental: Instrumental audio (numpy array)
        vocals: Vocal audio (numpy array)
        vocal_volume: Volume multiplier for vocals (0.0-1.0)
        instrumental_volume: Volume multiplier for instrumental (0.0-1.0)

    Returns:
        Mixed audio data
    """
    import numpy as np

    # Ensure same length - pad or trim vocals to match instrumental
    if len(vocals) < len(instrumental):
        # Pad vocals with silence at the end
        vocals = np.pad(vocals, (0, len(instrumental) - len(vocals)))
    elif len(vocals) > len(instrumental):
        # Trim vocals to match instrumental
        vocals = vocals[: len(instrumental)]

    # Mix the tracks
    mixed = (instrumental * instrumental_volume) + (vocals * vocal_volume)

    # Normalize to prevent clipping
    max_val = np.max(np.abs(mixed))
    if max_val > 1.0:
        mixed = mixed / max_val

    return mixed.astype(np.float32)


def _generate_vocals_for_song(lyrics: str, voice: str) -> tuple[object, int]:
    """Generate vocals using Bark for song mixing.

    Args:
        lyrics: Text/lyrics to sing
        voice: Bark voice preset

    Returns:
        Tuple of (vocal audio array, sample rate)
    """
    import functools

    import numpy as np
    import torch

    # Patch torch.load for Bark compatibility
    original_torch_load = torch.load

    @functools.wraps(original_torch_load)
    def patched_load(*args: object, **kwargs: object) -> object:
        kwargs.setdefault("weights_only", False)
        return original_torch_load(*args, **kwargs)

    torch.load = patched_load

    try:
        from bark import SAMPLE_RATE as BARK_SR
        from bark import generate_audio, preload_models

        print("Loading Bark model...")
        preload_models()

        print(f"Generating vocals with voice: {voice}")
        print(f"Lyrics: {lyrics!r}")

        sentences = _split_into_sentences(lyrics)
        vocal_segments = []

        for i, sentence in enumerate(sentences):
            if len(sentences) > 1:
                print(f"  Vocal segment {i + 1}/{len(sentences)}...")
            audio = generate_audio(sentence.strip(), history_prompt=voice)
            vocal_segments.append(audio)

        if len(vocal_segments) > 1:
            vocals = np.concatenate(vocal_segments)
        else:
            vocals = vocal_segments[0]

        return vocals, BARK_SR

    finally:
        torch.load = original_torch_load


def _generate_instrumental_for_song(
    music_prompt: str,
    duration: int,
) -> tuple[object, int]:
    """Generate instrumental music using MusicGen for song mixing.

    Args:
        music_prompt: Description of the music
        duration: Duration in seconds

    Returns:
        Tuple of (instrumental audio array, sample rate)
    """
    model_size = select_model_size(None)
    model, processor = load_model(model_size)

    print(f"Music prompt: {music_prompt!r}")
    print(f"Duration: {duration}s")

    device = str(next(model.parameters()).device)
    sample_rate = model.config.audio_encoder.sampling_rate

    if duration <= SEGMENT_DURATION:
        instrumental = generate_segment(
            music_prompt,
            model,
            processor,
            duration,
            device,
        )
    else:
        instrumental = _generate_long_audio(
            music_prompt,
            model,
            processor,
            duration,
        )

    return instrumental, sample_rate


def generate_song(
    lyrics: str,
    music_prompt: str,
    voice: str = "v2/en_speaker_6",
    output_dir: Path | None = None,
) -> Path:
    """Generate a complete song with vocals over instrumental music.

    This combines Bark for vocals and MusicGen for instrumental backing.

    Args:
        lyrics: The lyrics/text to sing (use ♪ for singing style)
        music_prompt: Description of the instrumental music
        voice: Bark voice preset (default: v2/en_speaker_6)
        output_dir: Directory to save output

    Returns:
        Path to the generated song file
    """
    import scipy.io.wavfile

    if output_dir is None:
        output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("GENERATING SONG WITH VOCALS")
    print("=" * 60)

    # Step 1: Generate vocals
    print("\n[1/3] Generating vocals...")
    vocals, bark_sr = _generate_vocals_for_song(lyrics, voice)
    vocal_duration = len(vocals) / bark_sr
    print(f"Vocals generated: {vocal_duration:.1f}s")

    # Step 2: Generate instrumental (match vocal duration + buffer)
    print("\n[2/3] Generating instrumental music...")
    music_duration = int(vocal_duration) + 2
    instrumental, musicgen_sr = _generate_instrumental_for_song(
        music_prompt,
        music_duration,
    )
    print(f"Instrumental generated: {len(instrumental) / musicgen_sr:.1f}s")

    # Step 3: Mix vocals and instrumental
    print("\n[3/3] Mixing vocals and instrumental...")
    vocals_resampled = _resample_audio(vocals, bark_sr, musicgen_sr)
    mixed = _mix_audio(instrumental, vocals_resampled)

    # Save the song
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_lyrics = "".join(c if c.isalnum() or c in " -_" else "" for c in lyrics[:20])
    safe_lyrics = safe_lyrics.strip().replace(" ", "_")
    filename = f"{timestamp}_song_{safe_lyrics}.wav"
    output_path = output_dir / filename

    scipy.io.wavfile.write(output_path, musicgen_sr, mixed)

    print("\n" + "=" * 60)
    print(f"Song saved to: {output_path}")
    print(f"Duration: {len(mixed) / musicgen_sr:.1f}s")
    print("=" * 60)

    return output_path


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


def interactive_mode(model: object, processor: object) -> None:
    """Run interactive prompt mode."""
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print("Enter prompts to generate music. Commands:")
    print("  :q or :quit  - Exit")
    print("  :d <seconds> - Set duration (e.g., ':d 15')")
    print("  :h or :help  - Show example prompts")
    print("=" * 60)

    duration = 10

    example_prompts = [
        "upbeat electronic dance music with heavy bass",
        "calm acoustic guitar melody with soft percussion",
        "epic orchestral soundtrack with dramatic strings",
        "lo-fi hip hop beats for studying",
        "80s synthwave with retro vibes",
        "jazz piano trio with upright bass",
        "ambient electronic music for relaxation",
        "rock guitar riff with drums",
        "classical piano sonata in minor key",
        "tropical house with steel drums",
    ]

    while True:
        try:
            prompt = input(f"\n[{duration}s] Enter prompt: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not prompt:
            continue

        if prompt.lower() in (":q", ":quit", "quit", "exit"):
            print("Exiting...")
            break

        if prompt.lower() in (":h", ":help", "help"):
            print("\nExample prompts:")
            for i, ex in enumerate(example_prompts, 1):
                print(f"  {i}. {ex}")
            continue

        if prompt.startswith(":d "):
            try:
                duration = int(prompt[3:].strip())
                duration = max(1, min(30, duration))  # Clamp to 1-30
                print(f"Duration set to {duration}s")
            except ValueError:
                print("Invalid duration. Use ':d <number>' e.g., ':d 15'")
            continue

        # Check if user entered a number to use example prompt
        if prompt.isdigit():
            idx = int(prompt) - 1
            if 0 <= idx < len(example_prompts):
                prompt = example_prompts[idx]
                print(f"Using: {prompt}")
            else:
                print(f"Invalid number. Enter 1-{len(example_prompts)}")
                continue

        try:
            generate_music(prompt, model, processor, duration_seconds=duration)
        except (RuntimeError, ValueError, OSError) as e:
            print(f"Error generating music: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate music or speech from text prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Music generation (MusicGen):
  %(prog)s "upbeat electronic dance music"
  %(prog)s --duration 60 "calm piano melody"
  %(prog)s --model small "jazz guitar solo"
  %(prog)s --interactive

  # Speech/vocals generation (Bark):
  %(prog)s --speech "Hello, how are you today?"
  %(prog)s --speech --voice v2/en_speaker_3 "Welcome!"
  %(prog)s --speech "♪ La la la, I love to sing ♪"

  # Full song with vocals over music:
  %(prog)s --song "♪ Hello world, this is my song ♪" --music "upbeat pop"

Model sizes for MusicGen (auto-selected based on VRAM if not specified):
  small  - ~500MB, fastest, lower quality (3GB+ VRAM)
  medium - ~3.3GB, good balance (8GB+ VRAM)
  large  - ~6.5GB, best quality (12GB+ VRAM)

Bark voices: v2/en_speaker_0 to v2/en_speaker_9
Bark tokens: [laughter] [laughs] [sighs] [music] [gasps] ♪ (singing)
        """,
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Text description of music/speech to generate",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=10,
        help="Duration in seconds (default: 10, any length supported)",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=["small", "medium", "large"],
        default=None,
        help="MusicGen model size (auto-select based on VRAM by default)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive mode (MusicGen only)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "-s",
        "--speech",
        action="store_true",
        help="Generate speech/vocals using Bark instead of music",
    )
    parser.add_argument(
        "-v",
        "--voice",
        default="v2/en_speaker_6",
        help="Bark voice preset (default: v2/en_speaker_6)",
    )
    parser.add_argument(
        "--song",
        action="store_true",
        help="Generate a full song with vocals over instrumental",
    )
    parser.add_argument(
        "--music",
        type=str,
        default="upbeat pop instrumental backing track",
        help="Music style for --song mode (default: upbeat pop)",
    )

    args = parser.parse_args()

    if not args.prompt and not args.interactive:
        parser.print_help()
        print("\nError: Either provide a prompt or use --interactive mode")
        sys.exit(1)

    # Check dependencies
    use_bark = args.speech or args.song
    if not check_dependencies(include_bark=use_bark):
        sys.exit(1)

    if args.song:
        # Full song generation mode (vocals + instrumental)
        generate_song(
            args.prompt,
            args.music,
            voice=args.voice,
            output_dir=args.output,
        )
    elif args.speech:
        # Bark speech generation mode
        generate_speech(
            args.prompt,
            voice=args.voice,
            output_dir=args.output,
        )
    else:
        # MusicGen music generation mode
        model_size = select_model_size(args.model)
        model, processor = load_model(model_size)

        if args.interactive:
            interactive_mode(model, processor)
        else:
            generate_music(
                args.prompt,
                model,
                processor,
                duration_seconds=args.duration,
                output_dir=args.output,
            )


if __name__ == "__main__":
    main()
