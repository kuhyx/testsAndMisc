# MusicGen - Local AI Music Generator

Generate music from text prompts using Meta's open-source MusicGen model.

## Quick Start

```bash
# 1. Run the setup script (creates venv, installs dependencies)
cd python_pkg/music_gen
./setup.sh

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Generate music!
python music_generator.py "upbeat electronic dance music with synths"
```

## Usage

### Single Generation

```bash
# Basic usage
python music_generator.py "jazz piano with soft drums"

# Set duration (in seconds, max ~30 recommended)
python music_generator.py --duration 20 "epic orchestral soundtrack"

# Use smaller/faster model
python music_generator.py --model small "rock guitar riff"

# Use larger/better quality model (needs 16GB+ VRAM)
python music_generator.py --model large "ambient electronic"
```

### Interactive Mode

```bash
python music_generator.py --interactive
```

In interactive mode:

- Type prompts to generate music
- `:d 15` - Set duration to 15 seconds
- `:h` - Show example prompts
- `:q` - Quit

## Model Sizes

| Model  | Size   | VRAM  | Quality | Speed  |
| ------ | ------ | ----- | ------- | ------ |
| small  | ~500MB | ~4GB  | Good    | Fast   |
| medium | ~3.3GB | ~8GB  | Better  | Medium |
| large  | ~6.5GB | ~16GB | Best    | Slow   |

## Requirements

- Python 3.10+
- 8GB+ RAM (16GB recommended)
- GPU recommended (CUDA or Apple Silicon MPS)
- Works on CPU but much slower

## Output

Generated audio files are saved to `./output/` as WAV files with timestamps.

## Example Prompts

- "upbeat electronic dance music with heavy bass"
- "calm acoustic guitar melody with soft percussion"
- "epic orchestral soundtrack with dramatic strings"
- "lo-fi hip hop beats for studying"
- "80s synthwave with retro vibes"
- "jazz piano trio with upright bass"
- "ambient electronic music for relaxation"
- "rock guitar riff with drums"
- "classical piano sonata in minor key"

## Troubleshooting

### Out of Memory

- Try `--model small` for lower VRAM usage
- Reduce duration with `--duration 5`
- Close other GPU applications

### Slow Generation

- Make sure GPU is detected (check output at startup)
- Use `--model small` for faster generation
- Reduce duration

### No Sound / Corrupted File

- Check if scipy is installed: `pip install scipy`
- Try a different audio player (VLC recommended)
