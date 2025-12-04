# MusicGen - Local AI Music & Speech Generator

Generate music and speech/vocals from text prompts using Meta's MusicGen and Suno's Bark.

## Features

- **Music Generation**: Create instrumental music from text descriptions (MusicGen)
- **Long Audio Support**: Generate music of any length via automatic segmentation with crossfading
- **Speech/Vocals**: Generate speech and singing with Bark (optional)
- **CUDA Optimized**: Auto-detects GPU and selects best model for your VRAM
- **No API Keys**: Runs 100% locally on your hardware

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

### Music Generation (MusicGen)

```bash
# Basic usage
python music_generator.py "jazz piano with soft drums"

# Set duration (any length supported via segmentation)
python music_generator.py --duration 60 "epic orchestral soundtrack"

# Generate a full 3-minute track
python music_generator.py --duration 180 "ambient electronic music"

# Use smaller/faster model
python music_generator.py --model small "rock guitar riff"

# Use larger/better quality model (needs 12GB+ VRAM)
python music_generator.py --model large "ambient electronic"
```

### Speech/Vocals Generation (Bark)

```bash
# First install Bark (not included in base setup)
pip install git+https://github.com/suno-ai/bark.git

# Generate speech
python music_generator.py --speech "Hello, how are you today?"

# Use different voice
python music_generator.py --speech --voice v2/en_speaker_3 "Welcome!"

# Generate singing
python music_generator.py --speech "♪ La la la, I love to sing ♪"

# With laughter and expression
python music_generator.py --speech "That's so funny! [laughter] I can't believe it."
```

**Bark special tokens:**

- `[laughter]`, `[laughs]`, `[sighs]`, `[gasps]` - expressions
- `[music]`, `[clears throat]` - sounds
- `♪` - singing
- `...` or `—` - hesitations

**Available voices:** `v2/en_speaker_0` through `v2/en_speaker_9`

### Interactive Mode

```bash
python music_generator.py --interactive
```

In interactive mode:

- Type prompts to generate music
- `:d 15` - Set duration to 15 seconds
- `:h` - Show example prompts
- `:q` - Quit

## Model Sizes (Auto-Selected by VRAM)

| Model  | Size   | VRAM  | Quality | Speed  |
| ------ | ------ | ----- | ------- | ------ |
| small  | ~500MB | 3GB+  | Good    | Fast   |
| medium | ~3.3GB | 8GB+  | Better  | Medium |
| large  | ~6.5GB | 12GB+ | Best    | Slow   |

## Requirements

- Python 3.10+
- NVIDIA GPU with CUDA (required for NVIDIA systems)
- Apple Silicon supported via MPS
- 8GB+ VRAM recommended for best results

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
- Reduce duration with `--duration 10`
- Close other GPU applications

### Slow Generation

- Make sure GPU is detected (check output at startup)
- Use `--model small` for faster generation
- Reduce duration

### No Sound / Corrupted File

- Check if scipy is installed: `pip install scipy`
- Try a different audio player (VLC recommended)

### CUDA Not Available

If you see "NVIDIA GPU detected but CUDA is not available":

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```
