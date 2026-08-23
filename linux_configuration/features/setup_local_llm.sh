#!/bin/bash
# setup_local_llm.sh — Self-hosted coding LLM stack for RTX 3090 on Arch Linux
#
# Stack:
#   - ollama-cuda  (inference backend, official Arch repo)
#   - qwen3:32b    (chosen model, Q4_K_M, 16 K context to guarantee full GPU fit)
#   - Open WebUI   (chat / model-manager frontend, Docker)
#
# Run as your normal user (NOT root). Requires sudo for pacman + systemd.
# Docker is accessed without sudo (user must be in the docker group — script verifies).

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────────
readonly MODEL="qwen3:32b"
# 16 K context keeps total VRAM under 24 GB on 3090:
#   weights ~20 GB  +  KV-cache Q8_0 @16K ~2 GB  +  buffers ~1.5 GB ≈ 23.5 GB
# Increase to 24576 or 32768 only after verifying 100% GPU in verify_gpu().
readonly CTX_LEN=16384
readonly OLLAMA_PORT=11434
readonly WEBUI_PORT=8080
readonly WEBUI_CONTAINER="open-webui"
readonly WEBUI_VOLUME="open-webui-data"
readonly OLLAMA_DROPIN="/etc/systemd/system/ollama.service.d/local-llm.conf"

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

# ── Helpers ───────────────────────────────────────────────────────────────────
section() { printf '\n\033[1;34m══ %s ══\033[0m\n' "$*"; }
ok()      { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
warn()    { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }
err()     { printf '\033[1;31m  ✗ %s\033[0m\n' "$*" >&2; }

wait_for_url() {
    local url="$1" label="$2" max="${3:-90}"
    local i=0
    warn "Waiting for $label (up to ${max}s)..."
    while ! curl -sf "$url" > /dev/null 2>&1; do
        if (( i >= max )); then
            err "$label did not become available after ${max}s"
            return 1
        fi
        sleep 1
        (( i++ ))
    done
    ok "$label is up"
}

# ── 0. Pre-flight ────────────────────────────────────────────────────────────
preflight() {
    section "Pre-flight checks"

    # GPU
    if ! command -v nvidia-smi &>/dev/null; then
        err "nvidia-smi not found — NVIDIA drivers not installed"
        exit 1
    fi
    local gpu_info gpu_name vram_mib
    gpu_info="$(nvidia-smi --query-gpu=name,memory.total \
        --format=csv,noheader,nounits 2>/dev/null | head -1)"
    gpu_name="${gpu_info%%, *}"   # everything before the first ", "
    vram_mib="${gpu_info##*, }"   # everything after the last ", "
    vram_mib="${vram_mib// /}"    # strip any trailing spaces
    ok "GPU: ${gpu_name} — ${vram_mib} MiB VRAM"

    if (( vram_mib < 22000 )); then
        warn "Less than 22 GB VRAM detected — ${MODEL} may partially offload to CPU"
        warn "Consider a smaller model if generation speed is below 10 tok/s"
    fi

    # Docker group
    if ! groups | grep -qw docker; then
        err "Current user is not in the 'docker' group"
        err "Fix: sudo usermod -aG docker \$USER  then re-login and re-run this script"
        exit 1
    fi
    ok "User is in docker group"

    # Docker daemon
    if ! docker info &>/dev/null; then
        warn "Docker daemon is not running — starting it..."
        sudo systemctl start docker
        docker info &>/dev/null || { err "Docker daemon failed to start"; exit 1; }
    fi
    ok "Docker daemon running"
}

# ── 1. Install ollama-cuda ────────────────────────────────────────────────────
install_ollama() {
    section "Installing ollama-cuda"

    if pacman -Qi ollama-cuda &>/dev/null; then
        ok "ollama-cuda already installed"
        return
    fi

    # Remove non-CUDA ollama if present to avoid conflicts
    if pacman -Qi ollama &>/dev/null; then
        warn "Removing non-CUDA ollama package before installing ollama-cuda..."
        sudo pacman -Rs --noconfirm ollama
    fi

    sudo pacman -S --noconfirm ollama-cuda
    ok "ollama-cuda installed"
}

# ── 2. Configure Ollama via systemd drop-in ───────────────────────────────────
configure_ollama() {
    section "Configuring Ollama (flash-attention + Q8_0 KV cache)"

    sudo mkdir -p "$(dirname "$OLLAMA_DROPIN")"
    sudo tee "$OLLAMA_DROPIN" > /dev/null << 'EOF'
[Service]
# Flash attention: halves VRAM on large contexts
Environment="OLLAMA_FLASH_ATTENTION=1"
# KV cache quantisation: Q8_0 saves ~30% VRAM vs full precision
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
# Listen on all interfaces so Docker containers can reach it
Environment="OLLAMA_HOST=0.0.0.0:11434"
# Single parallel request — best throughput for one user
Environment="OLLAMA_NUM_PARALLEL=1"
EOF
    ok "Systemd drop-in written: $OLLAMA_DROPIN"

    sudo systemctl daemon-reload
    # Restart if already running to pick up new env vars
    if systemctl is-active --quiet ollama; then
        sudo systemctl restart ollama
        ok "Ollama service restarted"
    fi
}

# ── 3. Enable & start Ollama ──────────────────────────────────────────────────
start_ollama() {
    section "Starting Ollama service"

    sudo systemctl enable --now ollama
    wait_for_url "http://localhost:${OLLAMA_PORT}/api/tags" "Ollama API" 30
}

# shellcheck source=lib/local_llm_model.sh
source "$SCRIPT_DIR/lib/local_llm_model.sh"

main() {
    log "Local LLM setup — model: ${MODEL}, GPU: RTX 3090, VRAM: 24 GB"

    preflight
    install_ollama
    configure_ollama
    start_ollama
    pull_model
    create_modelfile
    setup_webui
    enable_autostart
    verify_gpu
    verify_webui
    print_summary
}

main "$@"
