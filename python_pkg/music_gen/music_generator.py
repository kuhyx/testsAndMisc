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


def check_dependencies() -> bool:
    """Check if required packages are installed."""
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

    if missing:
        print("Missing dependencies. Install with:")
        print(f"  pip install {' '.join(missing)}")
        print("\nFor CUDA support:")
        print("  pip install torch --index-url https://download.pytorch.org/whl/cu121")
        print("  pip install transformers scipy")
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


def generate_music(
    prompt: str,
    model: object,
    processor: object,
    duration_seconds: int = 10,
    output_dir: Path | None = None,
) -> Path:
    """Generate music from a text prompt.

    Args:
        prompt: Text description of the music to generate
        model: The MusicGen model
        processor: The MusicGen processor
        duration_seconds: Length of audio to generate (max ~30s recommended)
        output_dir: Directory to save output (defaults to ./output)

    Returns:
        Path to the generated audio file
    """
    import scipy.io.wavfile
    import torch

    if output_dir is None:
        output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    print(f"\nGenerating {duration_seconds}s of music...")
    print(f"Prompt: {prompt!r}")

    device = next(model.parameters()).device

    # Prepare inputs
    inputs = processor(
        text=[prompt],
        padding=True,
        return_tensors="pt",
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Calculate tokens needed for duration
    # MusicGen generates ~50 tokens per second of audio
    max_new_tokens = int(duration_seconds * 50)

    # Generate
    with torch.no_grad():
        audio_values = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
        )

    # Get sample rate from model config
    sample_rate = model.config.audio_encoder.sampling_rate

    # Convert to numpy and save
    audio_data = audio_values[0, 0].cpu().numpy()

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
        description="Generate music from text prompts using MusicGen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "upbeat electronic dance music"
  %(prog)s --duration 20 "calm piano melody"
  %(prog)s --model small "jazz guitar solo"
  %(prog)s --interactive

Model sizes (auto-selected based on VRAM if not specified):
  small  - ~500MB, fastest, lower quality (3GB+ VRAM)
  medium - ~3.3GB, good balance (8GB+ VRAM)
  large  - ~6.5GB, best quality (12GB+ VRAM)
        """,
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Text description of music to generate",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=10,
        help="Duration in seconds (default: 10, max recommended: 30)",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=["small", "medium", "large"],
        default=None,
        help="Model size (default: auto-select based on VRAM, largest possible)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory (default: ./output)",
    )

    args = parser.parse_args()

    if not args.prompt and not args.interactive:
        parser.print_help()
        print("\nError: Either provide a prompt or use --interactive mode")
        sys.exit(1)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Select model size based on VRAM if not specified
    model_size = select_model_size(args.model)

    # Load model
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
