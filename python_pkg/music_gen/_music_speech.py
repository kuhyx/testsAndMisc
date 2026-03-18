"""Bark speech synthesis, vocal generation, and song mixing."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from python_pkg.music_gen._music_generation import (
    SEGMENT_DURATION,
    _generate_long_audio,
    generate_segment,
    load_model,
    select_model_size,
)

BARK_MAX_CHARS = 200  # Max characters per Bark segment (~13s of speech)

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

        preload_models()

        # Bark can only generate ~13s at a time
        # For longer text, we need to split into sentences
        audio_segments = []

        # Split on sentence boundaries for longer texts
        sentences = _split_into_sentences(text)

        for _i, sentence in enumerate(sentences):
            if len(sentences) > 1:
                pass

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

    return result or [text]


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

        preload_models()

        sentences = _split_into_sentences(lyrics)
        vocal_segments = []

        for _i, sentence in enumerate(sentences):
            if len(sentences) > 1:
                pass
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

    # Step 1: Generate vocals
    vocals, bark_sr = _generate_vocals_for_song(lyrics, voice)
    vocal_duration = len(vocals) / bark_sr

    # Step 2: Generate instrumental (match vocal duration + buffer)
    music_duration = int(vocal_duration) + 2
    instrumental, musicgen_sr = _generate_instrumental_for_song(
        music_prompt,
        music_duration,
    )

    # Step 3: Mix vocals and instrumental
    vocals_resampled = _resample_audio(vocals, bark_sr, musicgen_sr)
    mixed = _mix_audio(instrumental, vocals_resampled)

    # Save the song
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_lyrics = "".join(c if c.isalnum() or c in " -_" else "" for c in lyrics[:20])
    safe_lyrics = safe_lyrics.strip().replace(" ", "_")
    filename = f"{timestamp}_song_{safe_lyrics}.wav"
    output_path = output_dir / filename

    scipy.io.wavfile.write(output_path, musicgen_sr, mixed)

    return output_path
