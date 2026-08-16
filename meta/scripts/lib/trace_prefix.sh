#!/usr/bin/env bash

# ============================================================================
# Prefix redirection for trace_shell_split.sh: run a script whose job is
# PLACING FILES without letting it touch the live system, and make every write
# it performs visible in the trace.
#
# Why a separate mechanism from the PATH stubs: `cat > /etc/modprobe.d/x.conf`
# is a bash builtin plus a redirection. No PATH entry can intercept it. The
# stubs handle mutating *binaries*; this file handles mutating *redirections*.
#
# Two layers, applied together by build_prefix_argv:
#
#   1. Environment redirect. HOME and every XDG_* base are pointed into the
#      prefix. This covers the majority of real destinations, which are
#      $HOME-rooted variables (`unit_dir="$HOME/.config/systemd/user"`), with
#      NO change to the traced script. XDG_DATA_HOME is exported explicitly
#      rather than left to default off HOME: install_leechblock.sh reads it
#      directly and then runs `rsync -a --delete` at it, so inheriting a real
#      XDG_DATA_HOME from the caller's environment would delete live data.
#
#   2. bwrap bind mounts for the hardcoded-absolute residue (/etc/modprobe.d,
#      /usr/local/bin, /etc/systemd/system). Only the LEAF directories named on
#      the command line are bound -- binding /etc wholesale would shadow
#      /etc/passwd and /etc/os-release and produce fake failures that look like
#      a broken split. `--unshare-user --uid 0` additionally makes the run
#      believe it is root, which matters more than it sounds: the shared
#      require_root() does `exec sudo "$0"`, and under the sudo stub that
#      truncates the whole run to a single recorded call -- a near-empty trace
#      that diffs clean against any split at all.
#
# Anything absolute that was NOT bound fails EPERM / read-only rather than
# silently succeeding, so Decision 6 (never mutate the real system to verify a
# split) holds by construction rather than by discipline.
# ============================================================================

# XDG bases redirected into the prefix. Each is exported explicitly so a value
# already present in the caller's environment cannot leak a live path through.
readonly TRACE_XDG_VARS=(
	XDG_DATA_HOME:.local/share
	XDG_CONFIG_HOME:.config
	XDG_CACHE_HOME:.cache
	XDG_STATE_HOME:.local/state
)

# Populate the prefix with the directory skeleton and echo the env assignments
# needed to redirect a run into it. Caller exports them.
trace_prefix_env() {
	local prefix="$1" entry var rel
	mkdir -p "$prefix"
	printf 'HOME=%s\n' "$prefix"
	for entry in "${TRACE_XDG_VARS[@]}"; do
		var="${entry%%:*}"
		rel="${entry#*:}"
		mkdir -p "$prefix/$rel"
		printf '%s=%s\n' "$var" "$prefix/$rel"
	done
}

# Absolute destinations a script writes to, discovered statically. Used to tell
# the user which --bind-abs arguments a target needs, and to refuse clearly
# when bwrap cannot provide them.
#
# Both spellings must be caught, and the second is the one that bites:
# nvidia_troubleshoot.sh writes `cat >"$CONFIG_FILE"`, where CONFIG_FILE is
# built from MODPROBE_DIR="/etc/modprobe.d" many lines earlier. A scan that
# only looked for a literal path next to the `>` found nothing, the refusal
# never fired, and the run silently produced an empty manifest -- a false pass
# of exactly the kind this harness exists to prevent. So we also collect any
# variable ASSIGNED an absolute path under a system root, which over-reports
# (a path may only ever be read) but never under-reports. Over-reporting costs
# a redundant --bind-abs; under-reporting costs a live-system write.
trace_prefix_scan_absolute() {
	local target="$1"
	# `|| true` on each grep: a target with only one spelling of destination
	# makes the other grep exit 1, and under the caller's `set -e` that aborted
	# validate_requirements silently -- the refusal never fired and the run
	# proceeded with an empty manifest. Exactly the false pass being guarded
	# against, so the status is neutralised rather than relied upon.
	{
		# Literal destination directly after a redirection.
		{ grep -oE '>[[:space:]]*"?(/etc|/usr/local|/usr/share|/var/lib|/opt)[^"[:space:]]*' "$target" || true; } |
			sed -E 's/^>[[:space:]]*"?//' |
			xargs -r -n1 dirname
		# Absolute system paths assigned to a variable, which redirections and
		# `tee`/`mkdir` then reach indirectly.
		{ grep -oE '^[[:space:]]*(local[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*="?(/etc|/usr/local|/usr/share|/var/lib|/opt)[^"[:space:]]*' "$target" || true; } |
			sed -E 's/^[[:space:]]*(local[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*="?//' |
			while IFS= read -r path; do
				# Emit the path itself, never its parent. Taking dirname of a
				# config *directory* is what turned MODPROBE_DIR="/etc/modprobe.d"
				# into a bare `/etc`, and binding /etc wholesale shadows
				# /etc/passwd and /etc/os-release -- the traced script then fails
				# on an unrelated read and it looks like a broken split. A
				# variable holding a file path yields a directory that does not
				# exist inside the prefix, which bwrap creates on demand; that
				# is harmless, whereas an over-broad bind is not.
				printf '%s\n' "$path"
			done
	} | sort -u
}

# Build the argv that runs "$@" with the absolute destinations bound into the
# prefix. Echoes the command; empty output means "no bwrap needed".
#
# Each bound path is created inside the prefix first: bwrap requires the source
# of a --bind to exist.
trace_prefix_bwrap_argv() {
	local prefix="$1"
	shift
	local -a abs_dirs=()
	while [[ $# -gt 0 && $1 != "--" ]]; do
		abs_dirs+=("$1")
		shift
	done
	shift # drop the --

	if [[ ${#abs_dirs[@]} -eq 0 ]]; then
		return 0
	fi

	if ! command -v bwrap >/dev/null 2>&1; then
		echo "Error: --bind-abs needs bubblewrap (pacman -S bubblewrap)" >&2
		return 1
	fi

	local -a argv=(bwrap --dev-bind / / --unshare-user --uid 0 --gid 0)
	local dir
	for dir in "${abs_dirs[@]}"; do
		mkdir -p "$prefix/abs$dir"
		argv+=(--bind "$prefix/abs$dir" "$dir")
	done
	printf '%s\n' "${argv[@]}"
}

# The write manifest: what the run actually placed, with content hashes.
#
# This is the half of the change that satisfies "a silent stub is a trap".
# Redirecting a write without reporting it would recreate exactly the failure
# the doc warns about -- a dropped `cat > $HOME/.local/bin/foo.sh` would show
# up as nothing at all, and two traces would match while one lost a file.
#
# Content is normalized before hashing: the prefix path is replaced with a
# literal @PREFIX@. install_usage_monitoring.sh writes an UNQUOTED heredoc, so
# $HOME interpolates into the generated file's contents at write time; without
# normalization a mktemp-d prefix bakes a fresh random path into every artifact
# and no two traces ever match.
#
# What normalization does NOT remove is a timestamp the target itself embeds:
# nvidia_troubleshoot.sh writes `# Created by ... on $(date)`, so its hash
# changes every run and only its size is stable. That is a property of the
# traced script, not of the harness -- when diffing such a target, expect the
# sha to differ and compare the file LIST and sizes instead. Do not "fix" it by
# freezing the clock; that would hide a real content change too.
trace_prefix_manifest() {
	local prefix="$1" rel abs hash size
	if [[ ! -d $prefix ]]; then
		return 0
	fi
	while IFS= read -r rel; do
		abs="$prefix/$rel"
		size="$(stat -c '%s' "$abs")"
		hash="$(sed "s#${prefix}#@PREFIX@#g" "$abs" | sha256sum | cut -c1-16)"
		printf '%s size=%s sha=%s\n' "$rel" "$size" "$hash"
	done < <(find "$prefix" -type f -printf '%P\n' | sort)
}
