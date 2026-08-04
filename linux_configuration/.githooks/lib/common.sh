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

# Versions of the `language: system` tools that the gates depend on. Every
# entry is `command:expected:where`, where `where` names the file that pins
# the other side so a mismatch report can point at it.
#
# Why this table exists: these hooks run whatever binary happens to be on
# PATH. When the local copy and the pinned copy disagree about what counts as
# a finding -- or, for the formatters, about how a file should be formatted --
# a commit passes every local gate and then fails elsewhere on output the
# developer cannot reproduce. That is precisely what kept the pre-commit
# workflow red from b83ce5d onward, and it cost a full session to diagnose
# because the failure was invisible on the developer's machine.
#
# Two distinct risks are covered here. The linters (shellcheck and zsh) run
# in CI, so drift there shows up as an unreproducible CI failure. The
# formatters (prettier and shfmt) never run in CI -- they are pre-push and
# local-git-hook only -- but they REWRITE files, so drift between two
# developers silently reformats the repo back and forth, producing diff churn
# nobody intended.
readonly PINNED_TOOL_VERSIONS=(
	"shellcheck:0.11.0:.github/workflows/pre-commit.yml (SHELLCHECK_VERSION)"
	"prettier:3.9.5:.github/workflows/pre-commit.yml (PRETTIER_VERSION)"
	"shfmt:3.13.1:.github/workflows/pre-commit.yml (SHFMT_VERSION)"
	"zsh:5.9:.github/workflows/pre-commit.yml (zsh comes from apt; major.minor only)"
)

# Print the version of a pinned tool, normalised to bare digits.
#
# Each tool reports differently: shellcheck uses a `version:` line, shfmt and
# node prefix a `v`, zsh puts it in field 2. Normalising here keeps the
# comparison below a plain string match.
_tool_version() {
	local cmd="$1" raw=""

	case "$cmd" in
		shellcheck) raw="$(shellcheck --version 2>/dev/null | awk '/^version:/ { print $2 }')" ;;
		prettier) raw="$(prettier --version 2>/dev/null)" ;;
		shfmt) raw="$(shfmt --version 2>/dev/null)" ;;
		# zsh patch releases are not selectable via apt, so compare major.minor
		# only -- 5.9.2 locally and 5.9 in CI are not a meaningful divergence.
		zsh) raw="$(zsh --version 2>/dev/null | awk '{ print $2 }' | cut -d. -f1,2)" ;;
		*) return 1 ;;
	esac

	printf '%s' "${raw#v}"
}

# Warn when a local tool disagrees with the version pinned for CI.
#
# Deliberately warnings, not aborts: these arrive via pacman on a rolling
# distro, so bumps are routine and must not block a commit. What must not
# happen silently is the disagreement itself.
check_pinned_tool_versions() {
	local entry cmd expected where installed drifted=0

	for entry in "${PINNED_TOOL_VERSIONS[@]}"; do
		cmd="${entry%%:*}"
		where="${entry##*:}"
		expected="${entry#*:}"
		expected="${expected%%:*}"

		command -v "$cmd" >/dev/null 2>&1 || continue

		installed="$(_tool_version "$cmd")" || continue
		[[ -n $installed ]] || continue
		[[ $installed == "$expected" ]] && continue

		hook_log "⚠ ${cmd} ${installed} locally, pinned ${expected}"
		hook_log "  update: ${where}"
		hook_log "  update: linux_configuration/.githooks/lib/common.sh (PINNED_TOOL_VERSIONS)"
		drifted=1
	done

	if [[ $drifted -eq 1 ]]; then
		hook_log "  Results may differ between this machine and CI/other developers."
	fi
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

	check_pinned_tool_versions
}
