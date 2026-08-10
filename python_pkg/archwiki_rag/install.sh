#!/bin/bash

# ============================================================================
# Install the offline Arch Wiki RAG corpus and its refresh hook.
#
# Installs dependencies, builds the corpus, and registers a pacman hook that
# refreshes it whenever `arch-wiki-docs` is upgraded.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${PKG_DIR}/../.." && pwd)"
readonly SCRIPT_NAME PKG_DIR REPO_ROOT
readonly STORE_DIR="${HOME}/.local/share/knowledge-rag-archwiki"
readonly REFRESH_BIN="/usr/local/bin/archwiki-rag-refresh"
readonly HOOK_PATH="/etc/pacman.d/hooks/95-archwiki-rag.hook"
readonly MCP_CONFIG="${HOME}/.claude/mcp-optional/archwiki.json"

usage() {
    echo "Usage: $SCRIPT_NAME [--no-hook]"
    echo "Options:"
    echo "  --no-hook   Install dependencies and build the corpus, but skip the"
    echo "              pacman hook (which needs sudo)."
    echo "  -h, --help  Show this help"
    exit 0
}

INSTALL_HOOK=1

install_dependencies() {
    echo "==> Installing dependencies"
    # arch-wiki-docs is the corpus itself; the two Python packages do the
    # HTML -> Markdown conversion.
    sudo pacman -S --needed --noconfirm \
        arch-wiki-docs \
        python-beautifulsoup4 \
        python-markdownify
}

write_mcp_config() {
    echo "==> Writing MCP config: $MCP_CONFIG"
    mkdir -p "$(dirname "$MCP_CONFIG")"
    cat >"$MCP_CONFIG" <<EOF
{
  "mcpServers": {
    "archwiki": {
      "type": "stdio",
      "command": "${HOME}/.local/bin/knowledge-rag",
      "args": [],
      "env": {
        "KNOWLEDGE_RAG_DIR": "${STORE_DIR}"
      }
    }
  }
}
EOF
}

build_corpus() {
    echo "==> Building corpus (this takes ~1 min for conversion)"
    PYTHONPATH="$REPO_ROOT" python3 -m python_pkg.archwiki_rag sync --reindex
}

install_hook() {
    echo "==> Installing pacman hook"

    # The hook runs as root; this wrapper drops back to the invoking user and
    # detaches the CPU-bound reindex so the pacman transaction is not blocked
    # while the corpus re-embeds.
    sudo tee "$REFRESH_BIN" >/dev/null <<EOF
#!/bin/bash
# Refresh the offline Arch Wiki RAG corpus. Installed by $SCRIPT_NAME.
set -euo pipefail
exec systemd-run --machine="${USER}@" --user --quiet --collect \\
    --unit=archwiki-rag-refresh \\
    --setenv=PYTHONPATH="$REPO_ROOT" \\
    /usr/bin/python3 -m python_pkg.archwiki_rag sync --reindex
EOF
    sudo chmod 755 "$REFRESH_BIN"

    # Only Install/Upgrade/Remove are valid Operation values; an invalid hook
    # aborts EVERY pacman transaction, so this file must stay minimal.
    sudo mkdir -p "$(dirname "$HOOK_PATH")"
    sudo tee "$HOOK_PATH" >/dev/null <<EOF
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = arch-wiki-docs

[Action]
Description = Refreshing offline Arch Wiki RAG corpus...
When = PostTransaction
Exec = $REFRESH_BIN
EOF
}

main() {
    install_dependencies
    write_mcp_config
    build_corpus

    if [[ "$INSTALL_HOOK" -eq 1 ]]; then
        install_hook
    else
        echo "==> Skipping pacman hook (--no-hook)"
    fi

    echo "==> Done. Start a session with: claude-archwiki"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-hook)
            INSTALL_HOOK=0
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

main "$@"
