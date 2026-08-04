# shellcheck shell=bash

# ============================================================================
# Shared helpers for the tracked git hooks in linux_configuration/.githooks/.
#
# Sourced by the pre-commit and pre-push hooks and by
# meta/scripts/install_hooks.sh. Not executable on its own.
#
# Design note: these hooks FAIL CLOSED. A missing tool means "stop", never
# "skip the check" — a silently skipped gate is indistinguishable from a
# passing one, which is how a missing prettier went unnoticed long enough to
# let unformatted markdown reach main.
# ============================================================================

# Where git must look for hooks. Relative to the repo root so it survives the
# repo being cloned to a different path.
readonly HOOKS_PATH_REL="linux_configuration/.githooks"

# Every external binary the hooks shell out to, as "command:pacman-package".
# Derived from the `language: system` hooks in .pre-commit-config.yaml plus
# the tools this hook directory invokes directly (shfmt, jscpd via npm).
# Keep in sync when a new system-language hook is added.
readonly REQUIRED_TOOLS=(
	"pre-commit:python-pre-commit"
	"prettier:prettier"
	"shellcheck:shellcheck"
	"shfmt:shfmt"
	"zsh:zsh"
	"node:nodejs"
	"npm:npm"
	"python3:python"
)

# Emit a hook progress line.
hook_log() {
	printf '  %s\n' "$1"
}

# Abort the current hook with a message on stderr.
hook_abort() {
	printf '\n%s\n' "$1" >&2
	exit 1
}

# Ensure git actually routes hooks through this tracked directory.
#
# Self-heal: if core.hooksPath drifted (unset by a tool, pointed elsewhere, or
# never set on a fresh clone that then ran a hook some other way), put it back.
# Note the inherent limit — if hooksPath is unset AND .git/hooks is empty, no
# hook runs at all and nothing here executes. That gap is what
# meta/scripts/install_hooks.sh exists to close on a new machine.
ensure_hooks_path() {
	local current
	current="$(git config --get core.hooksPath || true)"

	if [[ $current == "$HOOKS_PATH_REL" ]]; then
		return 0
	fi

	git config core.hooksPath "$HOOKS_PATH_REL"
	hook_log "↻ repaired core.hooksPath: '${current:-<unset>}' → ${HOOKS_PATH_REL}"
}

# Ensure a single command is available, installing it via pacman when possible.
#
# $1 — command name to look for on PATH
# $2 — pacman package that provides it
#
# Tries a non-interactive install first; a package needing a TTY (password
# prompt, AUR) aborts with the exact command to run by hand rather than
# hanging on a prompt inside a git hook.
require_tool() {
	local cmd="$1" pkg="$2"

	if command -v "$cmd" >/dev/null 2>&1; then
		return 0
	fi

	hook_log "→ ${cmd} missing; installing ${pkg}..."

	if sudo -n pacman -S --noconfirm --needed "$pkg" >/dev/null 2>&1 &&
		command -v "$cmd" >/dev/null 2>&1; then
		hook_log "✓ ${cmd} installed"
		return 0
	fi

	hook_abort "Aborted: required tool '${cmd}' is missing and could not be installed automatically.
Run this yourself, then retry:
  ! sudo pacman -S ${pkg}"
}

# The shellcheck version CI pins (see .github/workflows/pre-commit.yml).
# Kept here so a drift between the two is visible locally, at commit time,
# rather than as a CI failure nobody can reproduce on their own machine.
readonly EXPECTED_SHELLCHECK_VERSION="0.11.0"

# Warn when the local shellcheck disagrees with the one CI pins.
#
# Deliberately a warning, not an abort: shellcheck comes from pacman on a
# rolling distro, so a version bump here is routine and should not block a
# commit. What must not happen silently is the situation this check exists
# for -- local and CI disagreeing about what counts as a finding, so a commit
# passes every local gate and then fails CI on output the developer cannot
# reproduce. When this fires, update EXPECTED_SHELLCHECK_VERSION and
# SHELLCHECK_VERSION in the workflow together.
check_shellcheck_version() {
	local installed

	command -v shellcheck >/dev/null 2>&1 || return 0

	installed="$(shellcheck --version 2>/dev/null | awk '/^version:/ { print $2 }')"
	[[ -n $installed ]] || return 0
	[[ $installed == "$EXPECTED_SHELLCHECK_VERSION" ]] && return 0

	hook_log "⚠ shellcheck ${installed} locally, CI pins ${EXPECTED_SHELLCHECK_VERSION}."
	hook_log "  Findings may differ between here and CI. Update both:"
	hook_log "  .github/workflows/pre-commit.yml (SHELLCHECK_VERSION)"
	hook_log "  linux_configuration/.githooks/lib/common.sh (EXPECTED_SHELLCHECK_VERSION)"
}

# Ensure every tool in REQUIRED_TOOLS is present. Fails closed on the first
# one that cannot be provided.
verify_toolchain() {
	local entry cmd pkg
	for entry in "${REQUIRED_TOOLS[@]}"; do
		cmd="${entry%%:*}"
		pkg="${entry##*:}"
		require_tool "$cmd" "$pkg"
	done

	check_shellcheck_version
}
