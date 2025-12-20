#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import timedelta
from typing import List, Optional


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def download_model_with_progress(model_name: str) -> str:
    """Download model files from HuggingFace with a visible progress bar.
    
    Returns the local path to the downloaded model.
    """
    try:
        from huggingface_hub import snapshot_download, hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError
    except ImportError:
        print("[WARN] huggingface_hub not available, falling back to default download", file=sys.stderr)
        return model_name
    
    # Map common model names to HF repo IDs
    model_map = {
        "tiny": "Systran/faster-whisper-tiny",
        "tiny.en": "Systran/faster-whisper-tiny.en",
        "base": "Systran/faster-whisper-base",
        "base.en": "Systran/faster-whisper-base.en",
        "small": "Systran/faster-whisper-small",
        "small.en": "Systran/faster-whisper-small.en",
        "medium": "Systran/faster-whisper-medium",
        "medium.en": "Systran/faster-whisper-medium.en",
        "large-v1": "Systran/faster-whisper-large-v1",
        "large-v2": "Systran/faster-whisper-large-v2",
        "large-v3": "Systran/faster-whisper-large-v3",
        "large": "Systran/faster-whisper-large-v3",
        "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
        "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
        "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
        "distil-small.en": "Systran/faster-distil-whisper-small.en",
    }
    
    repo_id = model_map.get(model_name, model_name)
    
    # Check if it looks like a repo ID
    if "/" not in repo_id and model_name not in model_map:
        # Assume it's a Systran model
        repo_id = f"Systran/faster-whisper-{model_name}"
    
    print(f"[INFO] Checking model: {repo_id}", flush=True)
    
    # Files we need to download (model.bin is the large one)
    required_files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
    
    try:
        # Use snapshot_download which handles caching and shows what's happening
        # First, let's check if model.bin needs downloading by checking cache
        from huggingface_hub import try_to_load_from_cache, HfFileSystem
        
        cache_path = try_to_load_from_cache(repo_id, "model.bin")
        if cache_path is not None:
            print(f"[INFO] Model already cached, loading from: {os.path.dirname(cache_path)}", flush=True)
            # Return the directory containing the cached files
            return os.path.dirname(cache_path)
        
        # Model not cached, need to download
        print(f"[INFO] Downloading model files from {repo_id}...", flush=True)
        print("[INFO] This may take several minutes for large models (~3GB for large-v3)", flush=True)
        
        # Get file sizes to show progress
        try:
            fs = HfFileSystem()
            files_info = fs.ls(repo_id, detail=True)
            total_size = sum(f.get('size', 0) for f in files_info if f.get('name', '').split('/')[-1] in required_files)
            print(f"[INFO] Total download size: ~{format_bytes(total_size)}", flush=True)
        except Exception:
            pass  # Size info is optional
        
        # Download with progress
        downloaded = 0
        start_time = time.time()
        
        for filename in required_files:
            file_start = time.time()
            print(f"[DOWNLOAD] {filename}...", end=" ", flush=True)
            try:
                local_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    resume_download=True,
                )
                elapsed = time.time() - file_start
                file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
                print(f"done ({format_bytes(file_size)}, {elapsed:.1f}s)", flush=True)
                downloaded += 1
                
                # Return directory on first successful download
                if downloaded == 1:
                    model_dir = os.path.dirname(local_path)
            except EntryNotFoundError:
                print("not found (optional)", flush=True)
            except Exception as e:
                print(f"error: {e}", flush=True)
        
        total_time = time.time() - start_time
        print(f"[INFO] Download complete in {total_time:.1f}s", flush=True)
        
        return model_dir
        
    except Exception as e:
        print(f"[WARN] Custom download failed ({e}), falling back to default", file=sys.stderr)
        return model_name


def format_timestamp(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    # Ensure SRT format HH:MM:SS,mmm
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(segments, srt_path: str):
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            start = format_timestamp(seg.start)
            end = format_timestamp(seg.end)
            text = (seg.text or "").strip()
            if not text:
                continue
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def write_txt(segments, txt_path: str):
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in segments:
            text = (seg.text or "").strip()
            if text:
                f.write(text + "\n")


def write_srt_with_speakers(segments, labels: List[int], path: str):
    with open(path, "w", encoding="utf-8") as f:
        for i, (seg, lab) in enumerate(zip(segments, labels), start=1):
            text = (seg.text or "").strip()
            if not text:
                continue
            spk = f"SPK{lab+1}"
            f.write(f"{i}\n{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}\n[{spk}] {text}\n\n")


def write_txt_with_speakers(segments, labels: List[int], path: str):
    with open(path, "w", encoding="utf-8") as f:
        for seg, lab in zip(segments, labels):
            text = (seg.text or "").strip()
            if text:
                spk = f"SPK{lab+1}"
                f.write(f"[{spk}] {text}\n")


def write_rttm(segments, labels: List[int], path: str, file_id: str = "audio"):
    # RTTM format: SPEAKER <file-id> 1 <start> <duration> <ortho> <stype> <name> <conf>
    with open(path, "w", encoding="utf-8") as f:
        for seg, lab in zip(segments, labels):
            start = float(getattr(seg, "start", 0.0) or 0.0)
            end = float(getattr(seg, "end", start) or start)
            dur = max(0.0, end - start)
            name = f"SPK{lab+1}"
            f.write(f"SPEAKER {file_id} 1 {start:.3f} {dur:.3f} <NA> <NA> {name} <NA>\n")


def hhmmss(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    total_seconds = int(seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_media_duration(path: str) -> float | None:
    """Try to get media duration in seconds using ffmpeg-python or ffprobe.
    Returns None if unavailable.
    """
    # Try ffmpeg-python first (if installed) which uses ffprobe under the hood
    try:
        import ffmpeg  # type: ignore

        probe = ffmpeg.probe(path)
        fmt = probe.get("format", {})
        if "duration" in fmt:
            return float(fmt["duration"])  # type: ignore
    except Exception:
        pass

    # Fallback: call ffprobe directly if available
    if shutil.which("ffprobe"):
        try:
            out = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                stderr=subprocess.DEVNULL,
            )
            return float(out.decode().strip())
        except Exception:
            return None
    return None


def _resample_linear(x, src_sr: int, tgt_sr: int):
    import numpy as np
    if src_sr == tgt_sr:
        return x
    ratio = float(tgt_sr) / float(src_sr)
    n_out = max(1, int(round(x.shape[-1] * ratio)))
    xp = np.linspace(0.0, 1.0, num=x.shape[-1], endpoint=False)
    xq = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    y = np.interp(xq, xp, x.astype(np.float32))
    return y.astype(np.float32)


def _kmeans_cosine(embs, k: int, iters: int = 50, seed: int = 0):
    import numpy as np
    rng = np.random.default_rng(seed)
    X = np.asarray(embs, dtype=np.float32)
    if X.ndim != 2 or X.shape[0] == 0:
        return np.zeros((0,), dtype=np.int64)
    # Normalize
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-8)
    # Init centroids as random samples
    idxs = rng.choice(X.shape[0], size=min(k, X.shape[0]), replace=False)
    C = X[idxs]
    # If fewer samples than k, pad with random
    if C.shape[0] < k:
        pad = rng.standard_normal(size=(k - C.shape[0], X.shape[1])).astype(np.float32)
        pad /= (np.linalg.norm(pad, axis=1, keepdims=True) + 1e-8)
        C = np.concatenate([C, pad], axis=0)
    for _ in range(iters):
        # Assign by cosine similarity (maximize dot product)
        sims = X @ C.T  # (n, k)
        labels = sims.argmax(axis=1)
        newC = np.zeros_like(C)
        for j in range(k):
            sel = X[labels == j]
            if sel.shape[0] == 0:
                newC[j] = C[j]
            else:
                v = sel.mean(axis=0)
                v /= (np.linalg.norm(v) + 1e-8)
                newC[j] = v
        if np.allclose(newC, C, atol=1e-4):
            break
        C = newC
    return labels


def _ffmpeg_transcode_to_wav16_mono(src_path: str) -> Optional[str]:
    """If ffmpeg is available, transcode input to a temporary 16k mono WAV and return its path."""
    if not shutil.which("ffmpeg"):
        return None
    import tempfile
    tmp = tempfile.NamedTemporaryFile(prefix="fw_diar_", suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()
    # Run ffmpeg quietly
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        src_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        tmp_path,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return tmp_path
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return None


def diarize_segments(audio_path: str, segments, num_speakers: int = 2) -> Optional[list]:
    """Simple diarization: compute speaker embeddings per segment and cluster with KMeans.
    Returns a list of speaker labels aligned with segments, or None on failure.
    """
    try:
        import numpy as np
        import soundfile as sf
        # Use non-deprecated import path
        from speechbrain.inference import EncoderClassifier
        import torch
    except Exception as e:
        print(f"[WARN] Diarization dependencies missing ({e}); skipping speaker labels.", file=sys.stderr)
        return None

    # Load audio
    temp_to_cleanup: Optional[str] = None
    try:
        wav, sr = sf.read(audio_path, dtype="float32", always_2d=False)
    except Exception as e:
        # Try ffmpeg transcoding fallback
        alt = _ffmpeg_transcode_to_wav16_mono(audio_path)
        if alt is None:
            print(f"[WARN] Could not read audio for diarization and no ffmpeg fallback available: {e}", file=sys.stderr)
            return None
        try:
            wav, sr = sf.read(alt, dtype="float32", always_2d=False)
            temp_to_cleanup = alt
        except Exception as e2:
            print(f"[WARN] Could not read transcoded audio for diarization: {e2}", file=sys.stderr)
            try:
                os.unlink(alt)
            except Exception:
                pass
            return None
    if wav.ndim == 2:  # mixdown
        wav = wav.mean(axis=1)
    # Resample to 16k for ECAPA
    wav16 = _resample_linear(wav, sr, 16000)

    # Load speaker embedding model (CPU is fine)
    try:
        classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": "cpu"},
            savedir=os.path.join(os.path.expanduser("~"), ".cache", "speechbrain_ecapa"),
        )
    except Exception as e:
        print(f"[WARN] Could not load speaker embedding model: {e}", file=sys.stderr)
        if temp_to_cleanup:
            try:
                os.unlink(temp_to_cleanup)
            except Exception:
                pass
        return None

    embs = []
    # Extract embedding per segment window
    for seg in segments:
        s = float(getattr(seg, "start", 0.0) or 0.0)
        e = float(getattr(seg, "end", s) or s)
        if e <= s:
            e = s + 0.2  # minimal window
        # Convert to samples in 16k
        i0 = int(s * 16000)
        i1 = int(e * 16000)
        # Add small margins to help very short segments
        pad = int(0.05 * 16000)
        i0 = max(0, i0 - pad)
        i1 = min(len(wav16), i1 + pad)
        if i1 - i0 < 1600:  # <0.1s, too short; expand if possible
            i1 = min(len(wav16), i0 + 1600)
        segment_wav = torch.tensor(wav16[i0:i1]).unsqueeze(0)
        with torch.no_grad():
            emb = classifier.encode_batch(segment_wav).squeeze(0).squeeze(0).cpu().numpy()
        embs.append(emb.astype("float32"))

    if len(embs) == 0:
        return None
    # Cluster
    labels = _kmeans_cosine(embs, k=max(1, int(num_speakers)))
    if temp_to_cleanup:
        try:
            os.unlink(temp_to_cleanup)
        except Exception:
            pass
    return labels.tolist()


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio with faster-whisper and write .txt and .srt")
    parser.add_argument("input", help="Path to audio/video file")
    parser.add_argument("--model", default=os.environ.get("FW_MODEL", "large-v3"), help="Model size or path (default: large-v3)")
    parser.add_argument("--language", default=None, help="Language code (e.g., en). Leave None for auto-detect")
    parser.add_argument("--device", default=os.environ.get("FW_DEVICE", "auto"), choices=["auto", "cpu", "cuda"], help="Device to run on")
    parser.add_argument("--compute-type", dest="compute_type", default=os.environ.get("FW_COMPUTE", "auto"), help="Compute type (auto,int8,float16,float32,int8_float16,etc.)")
    parser.add_argument("--outdir", default=None, help="Output directory (default: next to input)")
    parser.add_argument("--no-progress", action="store_true", help="Disable live progress output")
    parser.add_argument("--diarize", action="store_true", help="Enable speaker diarization (labels)")
    parser.add_argument("--num-speakers", type=int, default=int(os.environ.get("FW_NUM_SPEAKERS", "2")), help="Assumed number of speakers (default: 2)")
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        print("[ERROR] faster-whisper is not installed in this environment.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2

    inp = os.path.abspath(args.input)
    if not os.path.exists(inp):
        print(f"[ERROR] Input file not found: {inp}", file=sys.stderr)
        return 2

    outdir = os.path.abspath(args.outdir or os.path.dirname(inp) or ".")
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(inp))[0]
    srt_path = os.path.join(outdir, base + ".srt")
    txt_path = os.path.join(outdir, base + ".txt")

    # Device and compute_type heuristics
    device = args.device
    compute_type = args.compute_type
    if device == "auto":
        device = "cpu"
    if compute_type == "auto":
        # Prefer accuracy over speed by default
        compute_type = "float16" if device == "cuda" else "float32"

    print(f"[INFO] Loading model='{args.model}', device='{device}', compute_type='{compute_type}'")

    # Pre-download model files with explicit progress if not already cached
    model_path = args.model
    if not os.path.isdir(args.model):  # Not a local path, need to download from HF
        model_path = download_model_with_progress(args.model)

    # Show CTranslate2 conversion progress
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    ct2_logger = logging.getLogger("faster_whisper")
    ct2_logger.setLevel(logging.INFO)

    print("[INFO] Initializing model...", flush=True)
    model = WhisperModel(model_path, device=device, compute_type=compute_type)
    print("[INFO] Model loaded successfully.", flush=True)

    # Transcription with live progress
    total_duration = get_media_duration(inp)
    if total_duration:
        print(f"[INFO] Media duration: {hhmmss(total_duration)}")
    start_ts = time.time()

    iter_segments, info = model.transcribe(inp, language=args.language)
    collected = []
    processed = 0.0
    last_print = 0.0
    tty = sys.stderr.isatty()
    for seg in iter_segments:
        collected.append(seg)
        # Update processed time from segment end if available
        if getattr(seg, "end", None) is not None:
            processed = max(processed, float(seg.end))
        now = time.time()
        # Print each segment or throttle to ~5 per second
        if not args.no_progress and (tty or (now - last_print) >= 0.2):
            last_print = now
            if total_duration and total_duration > 0:
                pct = max(0.0, min(100.0, (processed / total_duration) * 100.0))
                elapsed = now - start_ts
                eta = None
                if processed > 0:
                    rate = processed / max(1e-6, elapsed)
                    remaining = max(0.0, total_duration - processed)
                    eta = remaining / max(1e-6, rate)
                line = f"[PROGRESS] {hhmmss(processed)} / {hhmmss(total_duration)} ({pct:5.1f}%)"
                if eta is not None and eta < 60 * 60 * 24:  # cap unrealistic values
                    line += f" ETA ~{hhmmss(eta)}"
            else:
                line = f"[PROGRESS] processed {hhmmss(processed)}"
            if tty:
                print("\r" + line, end="", file=sys.stderr, flush=True)
            else:
                print(line, file=sys.stderr, flush=True)

    # Finish progress line
    if not args.no_progress and sys.stderr.isatty():
        print("", file=sys.stderr)  # newline

    print(f"[INFO] Detected language: {getattr(info, 'language', None)} (prob={getattr(info, 'language_probability', None)})")
    print(f"[INFO] Segments: {len(collected)}")

    # Optionally diarize
    if args.diarize:
        labels = diarize_segments(inp, collected, num_speakers=args.num_speakers)
        if labels is not None and len(labels) == len(collected):
            diar_srt = os.path.join(outdir, base + ".diar.srt")
            diar_txt = os.path.join(outdir, base + ".diar.txt")
            rttm_path = os.path.join(outdir, base + ".rttm")
            write_srt_with_speakers(collected, labels, diar_srt)
            write_txt_with_speakers(collected, labels, diar_txt)
            write_rttm(collected, labels, rttm_path, file_id=base)
            print(f"[OK] Wrote: {diar_txt}\n[OK] Wrote: {diar_srt}\n[OK] Wrote: {rttm_path}")
        else:
            print("[WARN] Diarization failed or returned mismatched labels; writing plain outputs.", file=sys.stderr)

    # Write base outputs
    write_txt(collected, txt_path)
    write_srt(collected, srt_path)
    print(f"[OK] Wrote: {txt_path}\n[OK] Wrote: {srt_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
