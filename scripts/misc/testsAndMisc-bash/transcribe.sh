#!/usr/bin/env bash
set -euo pipefail

# Transcribe an audio file using faster-whisper with automatic setup.
# - Creates Python venv in .venv
# - Installs ffmpeg and espeak-ng (best-effort) for test audio generation
# - Installs faster-whisper (and CUDA stack if NVIDIA is present)
# - Runs tools/transcribe_fw.py to produce .txt and .srt next to the input

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
TOOLS_DIR="$PROJECT_DIR/tools"
PY_RUNNER="$TOOLS_DIR/transcribe_fw.py"
VENV_DIR="$PROJECT_DIR/.venv"

usage() {
	cat <<USAGE
Usage: $(basename "$0") [--online] [--prepare-model NAME --model-dir DIR] [-m model] [-l lang] [-o outdir] [audio_file]

Options:
	--online              Allow network to install deps and/or download models (default: offline)
	--prepare-model NAME  Download a model for offline use (implies --online)
	--model-dir DIR       Directory to store or load local models (default: ./models)
	-m model              Model size or path (tiny, base, small, medium, large-v3, etc.). Default: large-v3
	-l lang               Language code (e.g., en). Default: auto-detect
	-o outdir             Output directory (default: alongside input)
	[env] FW_DIARIZE=1    Enable diarization (speaker labels). Optional: FW_NUM_SPEAKERS=N. When --online, installs soundfile, speechbrain, and CPU-only torch/torchaudio.
	-h                    Show help
USAGE
}

log() {
	echo "[$(date +'%H:%M:%S')]" "$@"
}

detect_pkg_mgr() {
	if command -v apt-get >/dev/null 2>&1; then
		echo apt
		return
	fi
	if command -v dnf >/dev/null 2>&1; then
		echo dnf
		return
	fi
	if command -v yum >/dev/null 2>&1; then
		echo yum
		return
	fi
	if command -v pacman >/dev/null 2>&1; then
		echo pacman
		return
	fi
	if command -v zypper >/dev/null 2>&1; then
		echo zypper
		return
	fi
	echo none
}

has_libcublas12() {
	# Common system locations
	for d in \
		/usr/lib \
		/usr/lib64 \
		/usr/local/cuda/lib64 \
		/usr/local/cuda-12*/lib64 \
		/opt/cuda/lib64 \
		/opt/cuda/targets/x86_64-linux/lib; do
		if [[ -e "$d/libcublas.so.12" ]]; then
			return 0
		fi
	done
	# venv-provided NVIDIA CUDA libs
	if [[ -x "$VENV_DIR/bin/python" ]]; then
		local pyver
		pyver="$("$VENV_DIR"/bin/python -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
		if [[ -n $pyver ]]; then
			for d in "$VENV_DIR/lib/python$pyver/site-packages/nvidia/cublas/lib" \
				"$VENV_DIR/lib/python$pyver/site-packages/nvidia/cudnn/lib" \
				"$VENV_DIR/lib/python$pyver/site-packages/nvidia/cuda_runtime/lib"; do
				if [[ -e "$d/libcublas.so.12" ]]; then
					return 0
				fi
			done
		fi
	fi
	return 1
}

ensure_cuda_runtime() {
	local mgr
	mgr="$(detect_pkg_mgr)"
	if [[ $OFFLINE -eq 1 ]]; then
		if has_libcublas12; then return 0; fi
		echo "CUDA runtime (libcublas.so.12) not found and offline mode is enabled. Install CUDA 12 runtime or rerun with --online." >&2
		exit 6
	fi
	if has_libcublas12; then
		return 0
	fi
	if ! command -v sudo >/dev/null 2>&1; then
		log "sudo not found; skipping CUDA runtime install attempt."
	else
		log "CUDA cuBLAS 12 not found; attempting to install CUDA runtime (manager: $mgr)"
		set +e
		case "$mgr" in
		pacman)
			sudo pacman -Sy --noconfirm cuda cudnn || true
			;;
		apt)
			sudo apt-get update -y || true
			sudo apt-get install -y nvidia-cuda-toolkit || true
			;;
		dnf | yum)
			sudo "$mgr" install -y cuda cudnn || true
			;;
		zypper)
			sudo zypper install -y cuda cudnn || true
			;;
		*) log "Unknown package manager; cannot install CUDA automatically." ;;
		esac
		set -e
	fi
	# Re-check
	if ! has_libcublas12; then
		echo "CUDA runtime (libcublas.so.12) not found after attempted install. Please install CUDA 12 toolkit/runtime and re-run." >&2
		exit 6
	fi
}

install_system_deps() {
	have_cmd() { command -v "$1" >/dev/null 2>&1; }
	local need_ffmpeg=0 need_espeak=0
	have_cmd ffmpeg || need_ffmpeg=1
	have_cmd espeak-ng || need_espeak=1

	# If diarization requested and online, we may also try to ensure libsndfile
	local need_libsndfile=0
	if [[ ${FW_DIARIZE:-} == "1" ]]; then
		# Heuristic: check common library file
		if [[ ! -e /usr/lib/x86_64-linux-gnu/libsndfile.so && ! -e /usr/lib/libsndfile.so && ! -e /usr/lib64/libsndfile.so ]]; then
			need_libsndfile=1
		fi
	fi

	if [[ $need_ffmpeg -eq 0 && $need_espeak -eq 0 && $need_libsndfile -eq 0 ]]; then
		log "System deps present: ffmpeg, espeak-ng${FW_DIARIZE:+, libsndfile}"
		return 0
	fi

	if [[ $OFFLINE -eq 1 ]]; then
		echo "Missing system dependencies (ffmpeg/espeak-ng) but running in offline mode. Install them or rerun with --online." >&2
		exit 5
	fi

	local mgr
	mgr="$(detect_pkg_mgr)"
	log "Detected package manager: $mgr (installing missing: $([[ $need_ffmpeg -eq 1 ]] && echo ffmpeg)$([[ $need_espeak -eq 1 ]] && echo espeak-ng)$([[ $need_libsndfile -eq 1 ]] && echo libsndfile))"

	if ! command -v sudo >/dev/null 2>&1; then
		log "sudo not found; skipping system package installation attempt."
		return 0
	fi

	# Avoid exiting on install errors; continue best-effort
	set +e
	case "$mgr" in
	apt)
		sudo apt-get update -y || log "apt-get update failed; continuing"
		pkgs=(python3-venv python3-pip)
		[[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
		[[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
		if [[ $need_libsndfile -eq 1 ]]; then
			# Try both names across releases
			pkgs+=(libsndfile1)
			sudo apt-get install -y libsndfile1 || true
			# If that failed, try libsndfile2 (newer distros)
			sudo apt-get install -y libsndfile2 || true
		fi
		sudo apt-get install -y "${pkgs[@]}" || log "apt-get install failed; continuing"
		;;
	dnf)
		pkgs=(python3-venv python3-pip)
		[[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
		[[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
		[[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile)
		sudo dnf install -y "${pkgs[@]}" || log "dnf install failed; continuing"
		;;
	yum)
		pkgs=(python3-venv python3-pip)
		[[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
		[[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
		[[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile)
		sudo yum install -y "${pkgs[@]}" || log "yum install failed; continuing"
		;;
	pacman)
		pkgs=(python-virtualenv python-pip)
		[[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
		[[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
		[[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile)
		sudo pacman -Sy --noconfirm "${pkgs[@]}" || log "pacman install failed; continuing"
		;;
	zypper)
		pkgs=(python311-virtualenv python311-pip)
		[[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
		[[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
		[[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile1)
		sudo zypper install -y "${pkgs[@]}" || log "zypper install failed; continuing"
		;;
	*)
		log "Unknown package manager; please ensure ffmpeg and espeak-ng are installed."
		;;
	esac
	set -e
}

setup_venv() {
	if [[ ! -d $VENV_DIR ]]; then
		log "Creating venv at $VENV_DIR"
		python3 -m venv "$VENV_DIR"
	fi
	# shellcheck disable=SC1091
	source "$VENV_DIR/bin/activate"
	if [[ $OFFLINE -eq 0 ]]; then
		python -m pip install --upgrade pip wheel setuptools
	fi
}

install_python_deps() {
	# Install deps; if NVIDIA GPU is present, prefer CUDA-capable stack (cu12)
	local has_nvidia_flag="${1:-0}"
	log "Installing faster-whisper and dependencies"
	export PIP_DISABLE_PIP_VERSION_CHECK=1
	export PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT:-20}
	if [[ $OFFLINE -eq 1 ]]; then
		# Offline: do not install, just verify modules
		if ! python -c 'import faster_whisper' >/dev/null 2>&1; then
			echo "Python dependency 'faster_whisper' not found in offline mode. Run with --online to install." >&2
			exit 7
		fi
		# If diarization requested offline, check for its deps too (warn-only)
		if [[ ${FW_DIARIZE:-} == "1" ]]; then
			python - <<'PY' || true
try:
    import soundfile, speechbrain, torch  # noqa: F401
except Exception as e:
    print(f"[WARN] Diarization deps missing offline ({e}); speaker labels will be skipped.")
PY
		fi
		return 0
	fi
	if [[ $has_nvidia_flag -eq 1 ]]; then
		# If ctranslate2 is not installed, attempt CUDA-enabled wheel (quiet, with fallback)
		if ! "$VENV_DIR/bin/python" -c 'import ctranslate2' >/dev/null 2>&1; then
			log "Installing CUDA-enabled CTranslate2 (cu12 wheel)"
			python -m pip install -q --retries 1 --upgrade "ctranslate2<5,>=4.0" --extra-index-url https://download.opennmt.net/ctranslate2/cu12 ||
				log "Warning: could not reach cu12 wheel index; will proceed with available ctranslate2"
		fi
		# Ensure NVIDIA CUDA 12 runtime libs are available inside the venv
		python -m pip install -q --retries 1 --upgrade nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 ||
			log "Warning: failed to install NVIDIA cu12 runtime libs via pip"
	fi
	python -m pip install -q --retries 1 --upgrade faster-whisper ffmpeg-python

	# If diarization requested and online, install its Python deps best-effort
	if [[ ${FW_DIARIZE:-} == "1" ]]; then
		python -m pip install -q --retries 1 --upgrade soundfile speechbrain ||
			log "Warning: failed to install soundfile/speechbrain"
		# Torch and torchaudio CPU wheels (force to avoid mismatched CUDA builds)
		python -m pip install -q --retries 1 --upgrade --force-reinstall --index-url https://download.pytorch.org/whl/cpu torch torchaudio ||
			log "Warning: failed to install torch/torchaudio CPU wheels"
	fi
	python - <<'PY'
import sys
print(f"[PY] Python {sys.version.split()[0]} dependencies installed.")
PY
}

ensure_runner() {
	if [[ ! -f $PY_RUNNER ]]; then
		echo "Runner not found: $PY_RUNNER" >&2
		exit 3
	fi
}

generate_test_audio() {
	local tmpwav
	tmpwav="${PROJECT_DIR}/test_fw.wav"
	if command -v espeak-ng >/dev/null 2>&1; then
		log "Generating test audio via espeak-ng -> $tmpwav" >&2
		espeak-ng -w "$tmpwav" "This is a quick test of faster whisper transcription." >/dev/null 2>&1 || true
	fi
	# If espeak-ng failed or not present, try espeak
	if [[ ! -s $tmpwav ]] && command -v espeak >/dev/null 2>&1; then
		log "espeak-ng unavailable or failed; trying espeak -> $tmpwav" >&2
		espeak -w "$tmpwav" "This is a quick test of faster whisper transcription." >/dev/null 2>&1 || true
	fi
	# Fallback: generate tone via Python stdlib (no external deps)
	if [[ ! -s $tmpwav ]]; then
		log "Generating 3s 1kHz WAV via Python stdlib -> $tmpwav" >&2
		python3 -c 'import sys,wave,math,array;outfile=sys.argv[1];fr=16000;dur=3;freq=1000.0;ampl=0.3;n=fr*dur;data=array.array("h",[int(max(-1.0,min(1.0,ampl*math.sin(2*math.pi*freq*(i/fr))))*32767) for i in range(n)]);wf=wave.open(outfile,"w");wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(fr);wf.writeframes(data.tobytes());wf.close()' "$tmpwav" || true
	fi
	# Final fallback: tone via ffmpeg
	if [[ ! -s $tmpwav ]]; then
		log "Creating a 3s sine tone WAV via ffmpeg -> $tmpwav" >&2
		ffmpeg -f lavfi -i sine=frequency=1000:duration=3 -ar 16000 -ac 1 -f wav -y "$tmpwav" >/dev/null 2>&1 || true
	fi
	echo "$tmpwav"
}

prepare_model() {
	# Download a model for offline use into MODEL_DIR
	local name="$1"
	mkdir -p "$MODEL_DIR"
	# shellcheck disable=SC1091
	source "$VENV_DIR/bin/activate"
	log "Preparing model '$name' into $MODEL_DIR"
	python - <<PY
import sys, os
from faster_whisper import WhisperModel
name = os.environ.get('FW_PREPARE_NAME')
root = os.environ.get('FW_MODEL_DIR')
print(f"[PY] Preparing model '{name}' into {root}")
WhisperModel(name, device="cpu", compute_type="int8", download_root=root)
print("[PY] Model prepared.")
PY
}

main() {
	# Defaults
	OFFLINE=1
	PREPARE_MODEL=""
	MODEL_DIR="$PROJECT_DIR/models"
	MODEL="large-v3"
	LANGUAGE=""
	OUTDIR=""
	INPUT_FILE=""

	# Parse args
	PARSED=$(getopt -o m:l:o:h -l online,prepare-model:,model-dir: -- "$@") || {
		usage
		exit 2
	}
	eval set -- "$PARSED"
	while true; do
		case "$1" in
		-m)
			MODEL="$2"
			shift 2
			;;
		-l)
			LANGUAGE="$2"
			shift 2
			;;
		-o)
			OUTDIR="$2"
			shift 2
			;;
		-h)
			usage
			exit 0
			;;
		--online)
			OFFLINE=0
			shift
			;;
		--prepare-model)
			PREPARE_MODEL="$2"
			OFFLINE=0
			shift 2
			;;
		--model-dir)
			MODEL_DIR="$2"
			shift 2
			;;
		--)
			shift
			break
			;;
		*) break ;;
		esac
	done
	INPUT_FILE="${1:-}"

	if [[ $OFFLINE -eq 1 ]]; then
		export HF_HUB_OFFLINE=1
		export TRANSFORMERS_OFFLINE=1
	fi

	install_system_deps
	setup_venv

	# If asked to prepare a model, do that and exit
	if [[ -n $PREPARE_MODEL ]]; then
		if [[ $OFFLINE -eq 1 ]]; then
			echo "--prepare-model requires network; rerun with --online." >&2
			exit 2
		fi
		install_python_deps 0
		export FW_PREPARE_NAME="$PREPARE_MODEL"
		export FW_MODEL_DIR="$MODEL_DIR"
		prepare_model "$PREPARE_MODEL"
		log "Model '$PREPARE_MODEL' downloaded to $MODEL_DIR"
		exit 0
	fi

	# Detect NVIDIA GPU and enforce CUDA if present
	has_nvidia=0
	if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
		has_nvidia=1
	fi
	install_python_deps "$has_nvidia"
	ensure_runner

	local input="$INPUT_FILE"
	if [[ -z $input ]]; then
		input="$(generate_test_audio)"
		if [[ ! -s $input ]]; then
			echo "Failed to generate test audio. Please provide an audio file." >&2
			exit 4
		fi
	fi

	if [[ ! -f $input ]]; then
		echo "Input file not found: $input" >&2
		exit 2
	fi

	local args=("$input" "--model" "$MODEL")
	[[ -n $LANGUAGE ]] && args+=("--language" "$LANGUAGE")
	[[ -n $OUTDIR ]] && args+=("--outdir" "$OUTDIR")

	# Pass diarization via env if requested
	if [[ ${FW_DIARIZE:-} == "1" ]]; then
		args+=("--diarize")
		if [[ -n ${FW_NUM_SPEAKERS:-} ]]; then
			args+=("--num-speakers" "${FW_NUM_SPEAKERS}")
		fi
	fi

	if [[ $has_nvidia -eq 1 ]]; then
		ensure_cuda_runtime
		# Export common CUDA paths in case the env lacks them
		export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
		# Include system and possible venv-provided CUDA libs
		local pyver venv_cuda_paths=""
		if [[ -x "$VENV_DIR/bin/python" ]]; then
			pyver="$("$VENV_DIR"/bin/python -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
			if [[ -n $pyver ]]; then
				venv_cuda_paths="$VENV_DIR/lib/python$pyver/site-packages/nvidia/cublas/lib:$VENV_DIR/lib/python$pyver/site-packages/nvidia/cudnn/lib:$VENV_DIR/lib/python$pyver/site-packages/nvidia/cuda_runtime/lib"
			fi
		fi
		export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:${CUDA_HOME}/lib64:/usr/lib/x86_64-linux-gnu:/opt/cuda/lib64:/opt/cuda/targets/x86_64-linux/lib:${venv_cuda_paths}"
		export PATH="${PATH}:${CUDA_HOME}/bin"
		# shellcheck disable=SC1091
		source "$VENV_DIR/bin/activate"
		python -c 'from faster_whisper import WhisperModel; WhisperModel("tiny", device="cuda", compute_type="float16"); print("[PY] CUDA test init succeeded.")' || {
			echo "CUDA environment check failed. Aborting as requested." >&2
			exit 6
		}
		args+=("--device" "cuda")
	fi

	log "Transcribing: $input"
	# shellcheck disable=SC1091
	source "$VENV_DIR/bin/activate"
	if [[ $has_nvidia -eq 1 ]]; then
		if ! python "$PY_RUNNER" "${args[@]}"; then
			echo "CUDA execution requested due to detected NVIDIA GPU, but it failed. Aborting as requested (no CPU fallback)." >&2
			exit 6
		fi
	else
		# Offline: prefer local directory if present; otherwise use cache without network
		if [[ $OFFLINE -eq 1 ]]; then
			local local_model_path=""
			if [[ -d $MODEL ]]; then
				local_model_path="$MODEL"
			elif [[ -d "$MODEL_DIR/$MODEL" ]]; then
				local_model_path="$MODEL_DIR/$MODEL"
			fi
			if [[ -n $local_model_path ]]; then
				args=("$input" "--model" "$local_model_path")
				[[ -n $LANGUAGE ]] && args+=("--language" "$LANGUAGE")
				[[ -n $OUTDIR ]] && args+=("--outdir" "$OUTDIR")
			fi
		fi
		python "$PY_RUNNER" "${args[@]}"
	fi
}

main "$@"
