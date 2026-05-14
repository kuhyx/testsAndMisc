# clean_audio.sh — automatic speech cleaning (FFmpeg)

This script batch‑cleans noisy speech recordings with ffmpeg using simple, reliable filters tuned for ASR (e.g., faster‑whisper). By default it REQUIRES RNNoise (arnndn) and will try to auto‑discover or download a model. You can opt‑in to fallback filters with `--allow-fallback`.

## Install

- Required: ffmpeg. Most distros: `sudo pacman -S ffmpeg` or `sudo apt install ffmpeg`.
- Recommended: ffmpeg with `arnndn` filter and an RNNoise model file (e.g., from Mozilla RNNoise community models). The script will auto-detect common model locations or download one via `Bash/get_rnnoise_model.sh`. You can pass a specific model with `-m /path/to/model.nn`.

Make executable:

```bash
chmod +x Bash/clean_audio.sh
```

## Quick start

- Single file, default ASR preset (16k mono, denoise, high‑pass, limiter):

```bash
Bash/clean_audio.sh path/to/file.wav
```

This produces `path/to/file_clean.wav`.

- Whole folder, 4 parallel jobs, output to `cleaned/`:

```bash
Bash/clean_audio.sh path/to/folder -O cleaned -j 4
```

- Use an RNNoise model explicitly (if your ffmpeg has arnndn):

```bash
Bash/clean_audio.sh input.wav -m models/rnnoise_model.nn
```

If you omit `-m`, the script will look in common locations; if not found, it will attempt a download via `Bash/get_rnnoise_model.sh`.

Advanced options and compatibility:

- The cleaner requires RNNoise by default. To allow non-ML fallback filters (afftdn), add `--allow-fallback`.
- The script uses advanced filter settings when available (e.g., afftdn with `md`). If your ffmpeg build lacks these options, it will error with guidance. Add `--no-advanced` (or `--compat`) to avoid such params.

- Podcast preset (adds dynamics and loudness leveling):

```bash
Bash/clean_audio.sh input.wav --preset podcast
```

## Options

```text
Usage: clean_audio.sh <input-file|input-dir> [options]

Options:
  -O, --out-dir DIR         Output directory (default: alongside input file).
  -e, --ext EXT             Output extension/container: wav|flac (default: wav).
  -m, --model PATH          RNNoise model file for arnndn; falls back to afftdn if unavailable.
      --no-ml               Do not use arnndn even if model is provided; use afftdn.
      --preset NAME         asr (default) | podcast | aggressive
  -j, --jobs N              Parallel jobs for directory mode (default: 1).
  -f, --force               Overwrite outputs if they exist.
  -q, --quiet               Reduce ffmpeg logging noise.
      --lowpass FREQ        Optional low-pass cutoff (e.g., 8000). Disabled by default.
      --suffix SUF          Suffix for output basename (default: _clean).
```

## Designed for ASR (faster‑whisper)

Default output format is mono, 16 kHz, PCM 16‑bit WAV—ideal for most Whisper/faster‑whisper pipelines. You can feed the cleaned files directly into your transcription step.

If you prefer FLAC to save space without quality loss:

```bash
Bash/clean_audio.sh input.wav -e flac -O cleaned
```

## Presets

- asr (default): light, ASR‑friendly cleanup; prevents clipping.
- podcast: adds gentle dynamics and approximate loudness normalization (single‑pass `loudnorm`).
- aggressive: heavier gate/dynamics; can suppress background more, but may slightly hurt ASR accuracy—use sparingly.

## Tips

- If you see artifacts from RNNoise, try without a model (uses `afftdn`), or add a low‑pass (e.g., `--lowpass 8000`).
- For extremely boomy bar recordings, raise high‑pass by editing `HIGHPASS` in the script or add `--lowpass`.
- If your ffmpeg lacks `arnndn`, you can install a newer build or keep the fallback (afftdn works fine for many cases). - If your ffmpeg is missing features, you can use the helper:

```bash
chmod +x Bash/install_ffmpeg_with_arnndn.sh
Bash/install_ffmpeg_with_arnndn.sh
```

It will suggest distro options or build FFmpeg from source with `--enable-librnnoise`.

    RNNoise model downloader helper:
    ```bash
    chmod +x Bash/get_rnnoise_model.sh
    Bash/get_rnnoise_model.sh --yes
    ```
    This saves a model into `Bash/models/` which the cleaner will auto-discover.

## Troubleshooting

- “arnndn not available”: Your ffmpeg wasn’t built with it. The script will use `afftdn` instead.
- Output sounds thin: lower the high‑pass (edit `HIGHPASS=80` in script to `60`) or remove low‑pass.
- Level too low/high: choose the `podcast` preset for auto leveling, or add your own `loudnorm` in post.

## License

This helper script is provided under the repository’s LICENSE.
