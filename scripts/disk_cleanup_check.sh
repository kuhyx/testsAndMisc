#!/usr/bin/env bash
# disk_cleanup_check.sh — Analyze disk usage and suggest (or perform) cleanup.
#
# Usage:
#   ./disk_cleanup_check.sh           # Dry-run: report only
#   ./disk_cleanup_check.sh --clean   # Interactive: prompt before each action
#
# Safe by default: nothing is deleted without --clean AND user confirmation.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

CLEAN=false
if [[ "${1:-}" == "--clean" ]]; then
    CLEAN=true
fi

TOTAL_RECLAIMABLE=0

# ───────────────────── helpers ─────────────────────

human_readable() {
    local kb=$1
    if (( kb >= 1048576 )); then
        printf "%.1f GB" "$(echo "scale=1; $kb / 1048576" | bc)"
    elif (( kb >= 1024 )); then
        printf "%.1f MB" "$(echo "scale=1; $kb / 1024" | bc)"
    else
        printf "%d KB" "$kb"
    fi
}

dir_size_kb() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        du -sk "$dir" 2>/dev/null | awk '{print $1}'
    else
        echo 0
    fi
}

report() {
    local label="$1" size_kb="$2" detail="${3:-}"
    if (( size_kb > 0 )); then
        local hr
        hr=$(human_readable "$size_kb")
        printf "${YELLOW}%-40s${RESET} %10s" "$label" "$hr"
        if [[ -n "$detail" ]]; then
            printf "  ${CYAN}(%s)${RESET}" "$detail"
        fi
        printf "\n"
        TOTAL_RECLAIMABLE=$(( TOTAL_RECLAIMABLE + size_kb ))
    fi
}

# Returns 0 if user confirms, 1 otherwise. Always 1 in dry-run.
confirm() {
    local prompt="$1"
    if $CLEAN; then
        printf "${BOLD}  → %s [y/N]: ${RESET}" "$prompt"
        read -r ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    return 1
}

# Safe wrapper: confirm + action, never fails under errexit
try_clean() {
    local prompt="$1"
    shift
    if confirm "$prompt"; then
        "$@"
        printf "${GREEN}  ✓ Done${RESET}\n"
    fi
    return 0
}

# ───────────────────── checks ─────────────────────

printf "\n${BOLD}=== Disk Cleanup Analysis ===${RESET}\n\n"
printf "${BOLD}%-40s %10s${RESET}\n" "Category" "Reclaimable"
printf '%s\n' "$(printf '%.0s─' {1..60})"

# 1. Trash
trash_dir="$HOME/.local/share/Trash"
size=$(dir_size_kb "$trash_dir")
report "Trash" "$size" "empty trash"
if (( size > 0 )); then
    try_clean "Empty trash?" \
        rm -rf "${trash_dir}/files" "${trash_dir}/info" "${trash_dir}/expunged"
fi

# 2. Pacman cache
pacman_cache_size=$(dir_size_kb "/var/cache/pacman/pkg")
if (( pacman_cache_size > 0 )); then
    if command -v paccache &>/dev/null; then
        pkg_count=$(ls /var/cache/pacman/pkg/ 2>/dev/null | wc -l)
        report "Pacman cache ($pkg_count pkgs)" "$pacman_cache_size" \
            "sudo paccache -rk2"
        try_clean "Clean pacman cache (keep last 2 versions)?" \
            sudo paccache -rk2
    else
        report "Pacman cache (install pacman-contrib)" "$pacman_cache_size" \
            "pacman -S pacman-contrib && paccache -rk2"
    fi
fi

# 3. Yay build cache
yay_cache="$HOME/.cache/yay"
size=$(dir_size_kb "$yay_cache")
report "Yay AUR build cache" "$size" "rm -rf ~/.cache/yay"
if (( size > 0 )); then
    try_clean "Clear yay build cache?" rm -rf "${yay_cache:?}"
fi

# 4. Pip cache
pip_cache="$HOME/.cache/pip"
size=$(dir_size_kb "$pip_cache")
report "Pip cache" "$size" "pip cache purge"
if (( size > 0 )); then
    try_clean "Clear pip cache?" rm -rf "${pip_cache:?}"
fi

# 5. uv cache
uv_cache="$HOME/.cache/uv"
size=$(dir_size_kb "$uv_cache")
report "uv cache" "$size" "uv cache clean"
if (( size > 0 )); then
    try_clean "Clear uv cache?" rm -rf "${uv_cache:?}"
fi

# 6. HuggingFace cache
hf_cache="$HOME/.cache/huggingface"
size=$(dir_size_kb "$hf_cache")
report "HuggingFace models" "$size" "manual review recommended"

# 7. Suno cache
suno_cache="$HOME/.cache/suno"
size=$(dir_size_kb "$suno_cache")
report "Suno AI cache" "$size" "manual review recommended"

# 8. Go build cache
go_cache="$HOME/.cache/go-build"
size=$(dir_size_kb "$go_cache")
report "Go build cache" "$size" "go clean -cache"
if (( size > 0 )); then
    try_clean "Clear Go build cache?" rm -rf "${go_cache:?}"
fi

# 9. Yarn cache
yarn_cache="$HOME/.cache/yarn"
size=$(dir_size_kb "$yarn_cache")
report "Yarn cache" "$size" "yarn cache clean"
if (( size > 0 )); then
    try_clean "Clear yarn cache?" rm -rf "${yarn_cache:?}"
fi

# 10. npm cache
npm_cache="$HOME/.npm/_cacache"
size=$(dir_size_kb "$npm_cache")
report "npm cache" "$size" "npm cache clean --force"
if (( size > 0 )); then
    try_clean "Clear npm cache?" rm -rf "${npm_cache:?}"
fi

# 11. Electron cache
electron_cache="$HOME/.cache/electron"
size=$(dir_size_kb "$electron_cache")
report "Electron cache" "$size"
if (( size > 0 )); then
    try_clean "Clear Electron cache?" rm -rf "${electron_cache:?}"
fi

# 12. Thumbnails
thumb_cache="$HOME/.cache/thumbnails"
size=$(dir_size_kb "$thumb_cache")
report "Thumbnails cache" "$size"
if (( size > 0 )); then
    try_clean "Clear thumbnails?" rm -rf "${thumb_cache:?}"
fi

# 13. vscode-cpptools cache
cpptools_cache="$HOME/.cache/vscode-cpptools"
size=$(dir_size_kb "$cpptools_cache")
if (( size > 102400 )); then
    report "VS Code cpptools cache" "$size"
    try_clean "Clear cpptools cache?" rm -rf "${cpptools_cache:?}"
fi

# 14. Bazel cache
bazel_cache="$HOME/.cache/bazel"
size=$(dir_size_kb "$bazel_cache")
report "Bazel cache" "$size"
if (( size > 0 )); then
    try_clean "Clear bazel cache?" rm -rf "${bazel_cache:?}"
fi

# 15. Browser caches (report only)
for browser_cache in \
    "$HOME/.cache/thorium" \
    "$HOME/.cache/google-chrome" \
    "$HOME/.cache/mozilla" \
    "$HOME/.cache/BraveSoftware"; do
    if [[ -d "$browser_cache" ]]; then
        name=$(basename "$browser_cache")
        size=$(dir_size_kb "$browser_cache")
        if (( size > 102400 )); then
            report "Browser cache: $name" "$size" "close browser first"
        fi
    fi
done

# 16. Docker
if command -v docker &>/dev/null; then
    docker_dir="/var/lib/docker"
    size=$(dir_size_kb "$docker_dir" || echo 0)
    if (( size > 1048576 )); then
        report "Docker (images+build cache)" "$size" "docker system prune -a"
        try_clean "Docker system prune (removes all unused)?" \
            docker system prune -af --volumes
    fi
fi

# 17. Orphan packages
orphans=$(pacman -Qdtq 2>/dev/null || true)
orphan_count=0
if [[ -n "$orphans" ]]; then
    orphan_count=$(echo "$orphans" | wc -l)
fi
if (( orphan_count > 0 )); then
    orphan_size=$(echo "$orphans" | xargs pacman -Qi 2>/dev/null \
        | awk '/Installed Size/{
            size=$4; unit=$5;
            if (unit ~ /GiB/) total += size*1048576;
            else if (unit ~ /MiB/) total += size*1024;
            else if (unit ~ /KiB/) total += size;
        } END{printf "%d", total}' || echo 0)
    report "Orphan packages ($orphan_count)" "$orphan_size" \
        "sudo pacman -Rns \$(pacman -Qdtq)"
    if confirm "Remove $orphan_count orphan packages?"; then
        # shellcheck disable=SC2046
        sudo pacman -Rns $(pacman -Qdtq) --noconfirm
        printf "${GREEN}  ✓ Orphans removed${RESET}\n"
    fi
fi

# 18. Journal logs — vacuum to 200M
journal_line=$(journalctl --disk-usage 2>&1 || true)
journal_kb=0
if [[ "$journal_line" =~ ([0-9.]+)G ]]; then
    journal_kb=$(echo "${BASH_REMATCH[1]} * 1048576 / 1" | bc)
elif [[ "$journal_line" =~ ([0-9.]+)M ]]; then
    journal_kb=$(echo "${BASH_REMATCH[1]} * 1024 / 1" | bc)
fi
if (( journal_kb > 204800 )); then
    excess=$(( journal_kb - 204800 ))
    report "Journal logs (excess over 200M)" "$excess" "journalctl --vacuum-size=200M"
    try_clean "Vacuum journal to 200M?" \
        sudo journalctl --vacuum-size=200M
fi

# 19. AUR source dirs — old archives (>30 days)
aur_dir="$HOME/aur"
if [[ -d "$aur_dir" ]]; then
    old_archives_kb=$(find "$aur_dir" \
        \( -name "*.pkg.tar.zst" -o -name "*.tar.gz" -o -name "*.tar.xz" \
           -o -name "*.zip" -o -name "*.tar.bz2" \) \
        -mtime +30 -printf '%k\n' 2>/dev/null \
        | awk '{t+=$1} END{print t+0}')
    if (( old_archives_kb > 0 )); then
        report "AUR old archives (>30d)" "$old_archives_kb" \
            "find ~/aur '*.pkg.tar.zst' -mtime +30 -delete"
        if confirm "Delete old AUR archives (>30 days)?"; then
            find "$aur_dir" \
                \( -name "*.pkg.tar.zst" -o -name "*.tar.gz" -o -name "*.tar.xz" \
                   -o -name "*.zip" -o -name "*.tar.bz2" \) \
                -mtime +30 -delete
            printf "${GREEN}  ✓ Old AUR archives deleted${RESET}\n"
        fi
    fi
fi

# ───────────────────── report-only items ─────────────────────

printf "\n${BOLD}--- Report-only (manual review needed) ---${RESET}\n"

for manual_entry in \
    "$HOME/Downloads/too_big:~/Downloads/too_big" \
    "$HOME/Downloads:~/Downloads total" \
    "$HOME/inne:~/inne" \
    "/Games:/Games — still playing?"; do
    dir="${manual_entry%%:*}"
    label="${manual_entry#*:}"
    size=$(dir_size_kb "$dir")
    if (( size > 0 )); then
        hr=$(human_readable "$size")
        printf "${RED}%-40s %10s${RESET}  ${CYAN}(review manually)${RESET}\n" \
            "$label" "$hr"
    fi
done

# ───────────────────── summary ─────────────────────

printf "\n%s\n" "$(printf '%.0s─' {1..60})"
total_hr=$(human_readable "$TOTAL_RECLAIMABLE")
printf "${BOLD}Total auto-reclaimable:  ${GREEN}%s${RESET}\n" "$total_hr"

read -r used_kb total_kb used_pct <<< "$(df -k / | awk 'NR==2{print $3, $2, $5}')"
used_pct="${used_pct%\%}"
printf "${BOLD}Current usage:           %s / %s (%s%%)${RESET}\n" \
    "$(human_readable "$used_kb")" "$(human_readable "$total_kb")" "$used_pct"

if (( TOTAL_RECLAIMABLE > 0 )); then
    new_used=$(( used_kb - TOTAL_RECLAIMABLE ))
    if (( new_used < 0 )); then new_used=0; fi
    new_pct=$(( new_used * 100 / total_kb ))
    printf "${BOLD}After cleanup:           %s / %s (%d%%)${RESET}\n" \
        "$(human_readable "$new_used")" "$(human_readable "$total_kb")" "$new_pct"
fi

if ! $CLEAN; then
    printf "\n${CYAN}Run with --clean to interactively clean each category.${RESET}\n"
fi
printf "\n"
