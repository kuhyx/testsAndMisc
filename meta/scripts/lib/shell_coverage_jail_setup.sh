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
	mkdir -p "$JAIL/bin" "$JAIL/cov" "$JAIL/home" "$JAIL/etc"

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
		if [[ -d $path ]]; then
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
			printf 'mount --bind %q %q 2>/dev/null || printf "warn: bind failed: %s\\n" %q >&2\n' \
				"$JAIL/mnt$idx" "$path" '%s' "$path"
			idx=$((idx + 1))
		done
	} >"$JAIL/mounts.sh"
}
