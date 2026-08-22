#!/usr/bin/env bash

# ============================================================================
# Jail construction for shell_coverage_jail.sh.
#
# Split out on 2026-08-22 to hold both files under the repo's 250-line cap
# (shfmt's reformatting pushed the combined file to 289). Sourced, not
# executed: every function here expects $JAIL, $BIND_PATHS and $EXTRA_SHIMS
# from the caller.
# ============================================================================

readonly DEFAULT_SHIMS=(
	systemctl pkill pacman curl npm loginctl openrgb ddcutil i2cdetect
	modprobe reboot shutdown poweroff mount umount nft iptables crontab
	amixer notify-send yay makepkg
)

build_jail() {
	JAIL="$(mktemp -d)"
	# cov holds kcov's output (the line SET); trace holds the PS4 xtrace
	# output (the executed-line set). They are two SEPARATE passes because
	# kcov's ptrace and SHELLOPTS=xtrace cannot share a process -- measured:
	# under xtrace every kcov hit count collapses to 0.
	mkdir -p "$JAIL/bin" "$JAIL/cov" "$JAIL/trace" "$JAIL/home" "$JAIL/etc"

	# Sourced by every non-interactive bash in the trace pass (via BASH_ENV).
	# PS4 must be ASSIGNED here rather than inherited: bash under
	# `unshare --map-root-user` runs privileged and drops an inherited PS4,
	# which silently costs the trace its file:line prefix. `set -x` is
	# likewise re-applied per process, which is what reaches child shells.
	# Quoted heredoc: ${BASH_SOURCE}/${LINENO} must reach the traced shell
	# unexpanded so they evaluate per traced line.
	cat >"$JAIL/xtrace_env.sh" <<'XTRACE'
PS4='+PS4:${BASH_SOURCE}:${LINENO} '
set -x
XTRACE

	local tool
	for tool in "${DEFAULT_SHIMS[@]}" ${EXTRA_SHIMS[@]+"${EXTRA_SHIMS[@]}"}; do
		printf '#!/usr/bin/env bash\nprintf "%%s %%s\\n" "%s" "$*" >>"%s/calls.log"\nexit 0\n' \
			"$tool" "$JAIL" >"$JAIL/bin/$tool"
		chmod +x "$JAIL/bin/$tool"
	done

	# Fact 2: give the jail a passwd where the invoking user resolves. Inside
	# the userns our uid appears as 0, so the user is mapped to 0 here.
	# `sudo` cannot work inside a user namespace -- it calls setresuid, which
	# fails with EINVAL against an unmapped uid, and dies before running the
	# command. We are already uid 0 in here, so sudo has nothing to do: this
	# pass-through drops its own flags and execs the real command, which keeps
	# `sudo tee /etc/foo` writing into the jail exactly as the code intends.
	# It is NOT in DEFAULT_SHIMS, because recording-and-exiting would skip the
	# very writes these suites exist to assert on.
	cat >"$JAIL/bin/sudo" <<'SUDO'
#!/usr/bin/env bash
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|-H|-E|-S|-k) shift ;;
        -u) shift 2 ;;
        --) shift; break ;;
        *) break ;;
    esac
done
[[ $# -eq 0 ]] && exit 0
exec "$@"
SUDO
	chmod +x "$JAIL/bin/sudo"

	local user="${USER:-$(id -un)}"
	printf 'root:x:0:0::/root:/bin/bash\n%s:x:0:0::%s:/bin/bash\n' \
		"$user" "$JAIL/home" >"$JAIL/etc/passwd"
	printf 'root:x:0:\n%s:x:0:\n' "$user" >"$JAIL/etc/group"
	printf 'passwd: files\ngroup: files\n' >"$JAIL/etc/nsswitch.conf"

	# A bound path is replaced by an EMPTY dir, so anything the subject needs
	# to read from it must be seeded by the caller. /etc is seeded above.
	# A bound path is replaced by an EMPTY dir, so the subject's writes land
	# in the jail -- but a write to <bound>/sub/dir/file fails with ENOENT if
	# `sub/dir` does not exist, and a subject that aborts on that failure
	# looks exactly like one whose lines are unreachable. Mirroring the real
	# directory tree (names only, never file contents) keeps every write path
	# valid while still capturing the data.
	local path idx=0
	for path in ${BIND_PATHS[@]+"${BIND_PATHS[@]}"}; do
		mkdir -p "$JAIL/mnt$idx"
		# -r: an unreadable target (/root as a normal user) simply has no tree
		# to mirror. That is not an error -- the caller seeds what it needs with
		# --seed-dir -- but cd'ing into it would abort under `set -e`.
		if [[ -d $path && -r $path && -x $path ]]; then
			(cd "$path" && find . -type d -not -path '*/.*' -print0 2>/dev/null) |
				(cd "$JAIL/mnt$idx" && xargs -0 -r mkdir -p 2>/dev/null) || true
		fi
		if [[ $path == "/etc" ]]; then
			cp -a "$JAIL/etc/." "$JAIL/mnt$idx/"
		fi
		idx=$((idx + 1))
	done
}

# Written to a file and read back as an array so each case keeps its quoting;
# splitting an unquoted "$args" would need an SC2086 suppression, and this
# repo forbids suppressions.
write_cases() {
	local case_str
	for case_str in "${CASES[@]}"; do
		printf '%s\n' "$case_str"
	done >"$JAIL/cases"
}

build_mount_script() {
	local path idx=0
	{
		for path in ${BIND_PATHS[@]+"${BIND_PATHS[@]}"}; do
			# mkdir first: a bind onto a path this host does not have (/var/www on
			# a machine with no webserver) fails outright, and a bind that fails
			# silently is the exact misdiagnosis this runner exists to avoid --
			# the subject then writes to the REAL path or dies, and the report
			# shows unreachable lines either way. Hence fatal, not a warning.
			printf 'mkdir -p %q 2>/dev/null || true\n' "$path"
			printf 'mount --bind %q %q || { printf "Error: bind failed: %s\\n" %q >&2; exit 1; }\n' \
				"$JAIL/mnt$idx" "$path" '%s' "$path"
			idx=$((idx + 1))
		done
	} >"$JAIL/mounts.sh"
}

# A case that passes under kcov but fails under xtrace yields a PARTIAL trace,
# which under-reports and looks exactly like the defect the trace pass exists
# to fix. xtrace is slower, so a tight --timeout is the usual cause. Fail
# loudly rather than silently measuring less.
#
# Also collapses the two per-pass failure files into the one --fail-on-case-error
# reads, so that flag keeps its original meaning.
reconcile_pass_failures() {
	local kcov_fail=0 trace_fail=0
	if [[ -s "$JAIL/case_failures.kcov" ]]; then
		kcov_fail="$(wc -l <"$JAIL/case_failures.kcov")"
	fi
	if [[ -s "$JAIL/case_failures.trace" ]]; then
		trace_fail="$(wc -l <"$JAIL/case_failures.trace")"
	fi
	if [[ $trace_fail -gt $kcov_fail ]]; then
		printf 'Error: trace pass had %d failing case(s) vs %d under kcov; the\n' \
			"$trace_fail" "$kcov_fail" >&2
		printf '       trace is partial. xtrace is slower -- raise --timeout.\n' >&2
		exit 1
	fi
	if [[ -s "$JAIL/case_failures.kcov" ]]; then
		cp "$JAIL/case_failures.kcov" "$JAIL/case_failures"
	fi
}
