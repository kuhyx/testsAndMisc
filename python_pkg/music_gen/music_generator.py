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
from pathlib import Path
import sys
import warnings

from python_pkg.music_gen._music_generation import (
    CROSSFADE_DURATION,
    SEGMENT_DURATION,
    VRAM_THRESHOLD_LARGE,
    VRAM_THRESHOLD_MEDIUM,
    _calculate_segment_duration,
    _generate_long_audio,
    crossfade_audio,
    generate_music,
    generate_segment,
    get_device,
    get_vram_gb,
    load_model,
    select_model_size,
)
from python_pkg.music_gen._music_speech import (
    BARK_MAX_CHARS,
    BARK_VOICES,
    _generate_instrumental_for_song,
    _generate_vocals_for_song,
    _mix_audio,
    _resample_audio,
    _split_into_sentences,
    generate_song,
    generate_speech,
)

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Re-export all public symbols for backwards compatibility
__all__ = [
    "BARK_MAX_CHARS",
    "BARK_VOICES",
    "CROSSFADE_DURATION",
    "SEGMENT_DURATION",
    "VRAM_THRESHOLD_LARGE",
    "VRAM_THRESHOLD_MEDIUM",
    "_calculate_segment_duration",
    "_generate_instrumental_for_song",
    "_generate_long_audio",
    "_generate_vocals_for_song",
    "_mix_audio",
    "_resample_audio",
    "_split_into_sentences",
    "check_dependencies",
    "crossfade_audio",
    "generate_music",
    "generate_segment",
    "generate_song",
    "generate_speech",
    "get_device",
    "get_vram_gb",
    "interactive_mode",
    "load_model",
    "main",
    "select_model_size",
]


def check_dependencies(*, include_bark: bool = False) -> bool:
    """Check if required packages are installed.

    Args:
        include_bark: Whether to check for Bark dependencies as well.
    """
    import importlib.util

    missing = []

    if importlib.util.find_spec("torch") is None:
        missing.append("torch")

    if importlib.util.find_spec("transformers") is None:
        missing.append("transformers")

    if importlib.util.find_spec("scipy") is None:
        missing.append("scipy")

    if include_bark and importlib.util.find_spec("bark") is None:
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
