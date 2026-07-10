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
# shellcheck source=../../lib/common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../../lib/common.sh"

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

# ── 4. Create Modelfile with developer system prompt ─────────────────────────
create_modelfile() {
    section "Creating custom model with developer system prompt"

    # Condense Claude preferences into a system prompt (~1 K tokens).
    # Note: hooks, skills, and Claude Code MCP tools do NOT port to local models.
    # This only captures code-style, persona, and workflow preferences.
    local modelfile
    modelfile="$(mktemp --suffix=.modelfile)"

    cat > "$modelfile" << MODELFILE_EOF
FROM ${MODEL}

PARAMETER num_ctx ${CTX_LEN}
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER top_k 20

SYSTEM """
You are a coding assistant for Krzysztof (kuhy) Rudnicki, a software developer
who maintains personal automation and app monorepos.

## About me
- Stack: Python, Bash, C/C++, TypeScript, Dart/Flutter, Go
- OS: Arch Linux, i3 window manager
- Key repos: testsAndMisc (automation), linux-configuration, praca_magisterska

## Code style
Python:
- Use from __future__ import annotations for forward refs
- Google docstring convention (triple-quoted, brief summary + Args/Returns)
- Absolute imports only, no relative imports
- Type hints required on every function signature
- Prefer typed dataclasses over plain dicts

Shell (bash):
- Always set -euo pipefail at the top
- Double-quote all variable expansions
- Avoid fork-heavy patterns: prefer /proc, /sys, bash builtins over \$(...)
  in tight loops or status-bar scripts (fork-storm anti-pattern)
- Use jq/yq for JSON/YAML, not grep/awk
- NEVER embed multi-line Python logic inside shell heredocs — put it in a
  separate .py file and invoke with python3 path/to/file.py

TypeScript:
- Target ES2022, pure ESM (no CommonJS require)
- No any — use unknown + narrowing
- Discriminated unions for state machines
- async/await + structured error handling

## Behaviour I expect
- Keep responses brief and direct — no filler preamble
- Ask before making high-impact changes (schema changes, deleting data)
- If you spot a bad approach, say so before complying
- Development order: implement → run to verify → confirm → tests
  (tests are always LAST, not first)
- Include only one short comment per non-obvious block; no inline summaries
  of what the code obviously does

## Testing rules
- 100% branch coverage required for Python packages
- Use pytest + coverage; never mock the filesystem in integration tests
- Shell scripts: shellcheck must pass with no suppressions

## Git workflow
- Commit directly to main (no branches for personal repo)
- Conventional commit format: type: brief description
- Always run pre-commit hooks before committing
"""
MODELFILE_EOF

    local custom_model="${MODEL/:/-}-dev"
    ollama create "$custom_model" -f "$modelfile"
    rm -f "$modelfile"
    ok "Custom model created: $custom_model (includes developer system prompt)"
    ok "Load '$custom_model' in Open WebUI for kuhy-personalised responses"
}

# ── 5. Pull base model ────────────────────────────────────────────────────────
pull_model() {
    section "Pulling ${MODEL}"

    # Check if already present
    if curl -sf "http://localhost:${OLLAMA_PORT}/api/tags" \
            | grep -q "\"${MODEL}\""; then
        ok "${MODEL} already downloaded"
        return
    fi

    warn "Downloading ${MODEL} — approx 20 GB. This will take a while."
    warn "Progress is shown live; do not interrupt."
    ollama pull "${MODEL}"
    ok "${MODEL} downloaded"
}

# ── 6. Set up Open WebUI via Docker ───────────────────────────────────────────
setup_webui() {
    section "Setting up Open WebUI"

    # Remove existing container so we can apply any config changes cleanly
    if docker ps -a --format '{{.Names}}' | grep -qx "$WEBUI_CONTAINER"; then
        warn "Removing existing $WEBUI_CONTAINER container..."
        docker rm -f "$WEBUI_CONTAINER"
    fi

    docker pull ghcr.io/open-webui/open-webui:main

    docker run -d \
        --name "$WEBUI_CONTAINER" \
        --restart always \
        -p "${WEBUI_PORT}:8080" \
        -v "${WEBUI_VOLUME}:/app/backend/data" \
        -e OLLAMA_BASE_URL="http://host.docker.internal:${OLLAMA_PORT}" \
        --add-host=host.docker.internal:host-gateway \
        ghcr.io/open-webui/open-webui:main

    ok "Open WebUI container started on port ${WEBUI_PORT}"
}

# ── 7. Enable Docker on boot ──────────────────────────────────────────────────
enable_autostart() {
    section "Enabling auto-start on boot"

    # Docker daemon must start for the container (restart=always) to come up
    sudo systemctl enable docker
    ok "docker.service enabled on boot"
    ok "Ollama is already enabled; Open WebUI container uses restart=always"
}

# ── 8. Verify: GPU utilisation + generation speed ─────────────────────────────
verify_gpu() {
    section "Verifying GPU utilisation and generation speed"

    # Warm up with a short generation and measure tok/s
    warn "Running a warm-up generation (checking GPU offload + speed)..."
    local start_ts end_ts elapsed toks_per_sec
    start_ts="$(date +%s%N)"

    local response
    response="$(curl -sf "http://localhost:${OLLAMA_PORT}/api/generate" \
        -d "{\"model\":\"${MODEL}\",\"prompt\":\"Reply with exactly: ready\",\"stream\":false}" \
        --max-time 120)"

    end_ts="$(date +%s%N)"
    elapsed=$(( (end_ts - start_ts) / 1000000 ))  # milliseconds

    if [[ -z "$response" ]]; then
        err "No response from Ollama — generation failed"
        return 1
    fi

    # Parse eval_count (output tokens) and eval_duration (nanoseconds) from response
    local eval_count eval_duration_ns
    eval_count="$(printf '%s' "$response" | grep -o '"eval_count":[0-9]*' | grep -o '[0-9]*' || echo 0)"
    eval_duration_ns="$(printf '%s' "$response" | grep -o '"eval_duration":[0-9]*' | grep -o '[0-9]*' || echo 1)"

    if (( eval_count > 0 && eval_duration_ns > 0 )); then
        toks_per_sec=$(( eval_count * 1000000000 / eval_duration_ns ))
        ok "Generation speed: ${toks_per_sec} tok/s (${eval_count} tokens in ${elapsed}ms)"
        if (( toks_per_sec < 10 )); then
            warn "Speed is below 10 tok/s — model may be partially CPU-offloaded"
            warn "Run: ollama ps  to check GPU layer count"
            warn "If GPU% < 100, try reducing CTX_LEN in this script or use a smaller quant"
        fi
    else
        warn "Could not parse tok/s from response; check manually with: ollama ps"
    fi

    # Check GPU offload via ollama ps
    warn "Checking GPU layer utilisation..."
    if command -v ollama &>/dev/null; then
        ollama ps 2>/dev/null | head -10 || true
    fi

    ok "Verify done — see ollama ps output above for GPU% column"
}

# ── 9. WebUI readiness check ──────────────────────────────────────────────────
verify_webui() {
    section "Waiting for Open WebUI to become ready"
    wait_for_url "http://localhost:${WEBUI_PORT}" "Open WebUI" 60
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
    local custom_model="${MODEL/:/-}-dev"
    printf '\n\033[1;32m'
    printf '═══════════════════════════════════════════════════════\n'
    printf ' Local LLM setup complete!\n'
    printf '═══════════════════════════════════════════════════════\n'
    printf ' Open WebUI:     http://localhost:%s\n' "$WEBUI_PORT"
    printf ' Ollama API:     http://localhost:%s\n' "$OLLAMA_PORT"
    printf ' Primary model:  %s  (%d K context)\n' "$MODEL" $(( CTX_LEN / 1024 ))
    printf ' Dev model:      %s  (with code-style system prompt)\n' "$custom_model"
    printf '\n'
    printf ' GPU fit notes:\n'
    printf '   Current context: %d K (safe for 24 GB VRAM)\n' $(( CTX_LEN / 1024 ))
    printf '   To try 24 K:    edit CTX_LEN=24576 in this script\n'
    printf '   To try 32 K:    edit CTX_LEN=32768 (risks partial CPU offload)\n'
    printf '   After changes:  re-run this script; check tok/s in verify step\n'
    printf '\n'
    printf ' To use with Claude Code:\n'
    printf '   Claude Code uses the Anthropic API — it cannot point at Ollama\n'
    printf '   directly (different wire format). Use Open WebUI for local-model\n'
    printf '   coding sessions, or ask about setting up a LiteLLM proxy.\n'
    printf '═══════════════════════════════════════════════════════\n'
    printf '\033[0m\n'
}

# ── Main ──────────────────────────────────────────────────────────────────────
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
