#!/usr/bin/env python3
"""Helper utilities for transcribe.sh - replaces inline Python snippets."""

import argparse
import array
import math
import os
import sys
import wave


def get_python_version() -> str:
    """Return Python major.minor version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def check_faster_whisper() -> bool:
    """Check if faster_whisper is importable. Exit 7 if not."""
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def check_diarization_deps() -> bool:
    """Check if diarization dependencies are available. Returns False with warning if missing."""
    try:
        import soundfile  # noqa: F401
        import speechbrain  # noqa: F401
        import torch  # noqa: F401

        return True
    except Exception as e:
        print(
            f"[WARN] Diarization deps missing offline ({e}); speaker labels will be skipped."
        )
        return False


def check_ctranslate2() -> bool:
    """Check if ctranslate2 is importable."""
    try:
        import ctranslate2  # noqa: F401

        return True
    except ImportError:
        return False


def print_deps_installed():
    """Print confirmation that Python dependencies are installed."""
    print(f"[PY] Python {sys.version.split()[0]} dependencies installed.")


def generate_sine_wav(
    outfile: str,
    frequency: float = 1000.0,
    duration: int = 3,
    sample_rate: int = 16000,
    amplitude: float = 0.3,
) -> bool:
    """Generate a sine wave WAV file using only Python stdlib.

    Args:
        outfile: Output WAV file path
        frequency: Tone frequency in Hz (default: 1000)
        duration: Duration in seconds (default: 3)
        sample_rate: Sample rate in Hz (default: 16000)
        amplitude: Amplitude 0.0-1.0 (default: 0.3)

    Returns:
        True on success, False on failure
    """
    try:
        n_samples = sample_rate * duration
        data = array.array(
            "h",
            [
                int(
                    max(
                        -1.0,
                        min(
                            1.0,
                            amplitude
                            * math.sin(2 * math.pi * frequency * (i / sample_rate)),
                        ),
                    )
                    * 32767
                )
                for i in range(n_samples)
            ],
        )
        with wave.open(outfile, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(data.tobytes())
        return True
    except Exception as e:
        print(f"[ERROR] Failed to generate WAV: {e}", file=sys.stderr)
        return False


def prepare_model(model_name: str, model_dir: str) -> bool:
    """Download a whisper model for offline use.

    Args:
        model_name: Model name (tiny, base, small, medium, large-v3, etc.)
        model_dir: Directory to store the model

    Returns:
        True on success, False on failure
    """
    try:
        from faster_whisper import WhisperModel

        # Enable HuggingFace Hub progress bars for model download
        try:
            from huggingface_hub import logging as hf_logging

            hf_logging.set_verbosity_info()
            import huggingface_hub

            huggingface_hub.constants.HF_HUB_DISABLE_PROGRESS_BARS = False
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
        except ImportError:
            pass

        print(f"[PY] Preparing model '{model_name}' into {model_dir}")
        print(
            "[INFO] Downloading model files (progress bar should appear below)...",
            flush=True,
        )
        WhisperModel(
            model_name, device="cpu", compute_type="int8", download_root=model_dir
        )
        print("[PY] Model prepared.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to prepare model: {e}", file=sys.stderr)
        return False


def test_cuda() -> bool:
    """Test CUDA initialization with faster-whisper.

    Returns:
        True if CUDA works, False otherwise
    """
    try:
        from faster_whisper import WhisperModel

        WhisperModel("tiny", device="cuda", compute_type="float16")
        print("[PY] CUDA test init succeeded.")
        return True
    except Exception as e:
        print(f"[ERROR] CUDA test failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Helper utilities for transcribe.sh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  python-version       Print Python major.minor version
  check-faster-whisper Check if faster_whisper is installed (exit 7 if not)
  check-diarization    Check diarization deps (warn if missing)
  check-ctranslate2    Check if ctranslate2 is installed (exit 1 if not)
  deps-installed       Print deps installed confirmation message
  generate-wav FILE    Generate a 3s 1kHz sine wave WAV file
  prepare-model        Download model for offline use (requires --model and --model-dir)
  test-cuda            Test CUDA initialization
""",
    )
    parser.add_argument(
        "command",
        choices=[
            "python-version",
            "check-faster-whisper",
            "check-diarization",
            "check-ctranslate2",
            "deps-installed",
            "generate-wav",
            "prepare-model",
            "test-cuda",
        ],
        help="Command to run",
    )
    parser.add_argument("--file", help="Output file path (for generate-wav)")
    parser.add_argument("--model", help="Model name (for prepare-model)")
    parser.add_argument("--model-dir", help="Model directory (for prepare-model)")

    args = parser.parse_args()

    if args.command == "python-version":
        print(get_python_version())
    elif args.command == "check-faster-whisper":
        if not check_faster_whisper():
            print(
                "Python dependency 'faster_whisper' not found in offline mode. Run with --online to install.",
                file=sys.stderr,
            )
            sys.exit(7)
    elif args.command == "check-diarization":
        check_diarization_deps()
    elif args.command == "check-ctranslate2":
        if not check_ctranslate2():
            sys.exit(1)
    elif args.command == "deps-installed":
        print_deps_installed()
    elif args.command == "generate-wav":
        if not args.file:
            print("--file is required for generate-wav", file=sys.stderr)
            sys.exit(2)
        if not generate_sine_wav(args.file):
            sys.exit(1)
    elif args.command == "prepare-model":
        if not args.model or not args.model_dir:
            print(
                "--model and --model-dir are required for prepare-model",
                file=sys.stderr,
            )
            sys.exit(2)
        if not prepare_model(args.model, args.model_dir):
            sys.exit(1)
    elif args.command == "test-cuda":
        if not test_cuda():
            sys.exit(1)


if __name__ == "__main__":
    main()
