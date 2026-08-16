#!/usr/bin/env bash

# ============================================================================
# PATH stub generation for trace_shell_split.sh.
#
# Split out of trace_shell_split.sh when --prefix pushed that file past the
# 250-line cap. The harness is not exempt from the rule it exists to serve.
#
# These stubs shadow mutating BINARIES. Mutating REDIRECTIONS (`cat > /etc/...`)
# cannot be intercepted this way at all and are handled by lib/trace_prefix.sh.
# ============================================================================

# Commands that change the system, the phone, or the package set. Each becomes
# a stub that records its invocation and exits 0. Extend deliberately: a
# missing name here means the real binary runs.
#
# Deliberately NOT here: `git`, `curl`, `wget`, `makepkg`. Those are stubbed
# per-run via --stub, because plenty of scripts read git state harmlessly and a
# blanket git stub would change what they see rather than protect anything.
# Grep the target for network and build verbs before tracing it.
readonly DEFAULT_STUBBED_COMMANDS=(
	sudo pacman yay paru systemctl systemd-run
	adb fastboot
	nft iptables ip6tables firewall-cmd
	mount umount swapoff modprobe
	useradd usermod visudo chpasswd
	mkinitcpio grub-mkconfig bootctl
	npm pip pip3 flutter gradle
	reboot shutdown poweroff halt
)

# One stub per mutating command: append the call to the trace, succeed.
# Stubs report success because the point is to reach later code paths, not to
# simulate failure. A script whose logic branches on a real exit status needs a
# hand-written stub instead -- note that in the split's evidence file.
#
# A stub may carry an output value as `name=text` (from --stub). This matters
# more than it looks: a stub that prints nothing makes every `size=$(du ...)`
# empty, so every `((size > 0))` is false and the trace walks straight past all
# the branches you wanted to compare. Two such traces are identical and
# meaningless. Give value-producing commands a plausible non-zero output.
#
# Extra stubs are passed as the trailing arguments rather than read from a
# global, so this stays callable independently of the caller's variables.
write_stubs() {
	local bin_dir="$1" entry name value
	shift
	mkdir -p "$bin_dir"
	for entry in "${DEFAULT_STUBBED_COMMANDS[@]}" "$@"; do
		name="${entry%%=*}"
		value=""
		if [[ $entry == *=* ]]; then
			value="${entry#*=}"
		fi
		# Quoted heredoc: everything is literal, so $* and $TRACE_FILE reach
		# the generated stub instead of expanding here. Only $name and $value
		# are interpolated, via the unquoted echo lines around it.
		{
			echo "#!/usr/bin/env bash"
			echo "STUB_NAME=$(printf '%q' "$name")"
			echo "STUB_VALUE=$(printf '%q' "$value")"
			cat <<'STUB'
printf '%s %s\n' "$STUB_NAME" "$*" >>"$TRACE_FILE"
if [[ -n $STUB_VALUE ]]; then
	printf '%s\n' "$STUB_VALUE"
fi
exit 0
STUB
		} >"$bin_dir/$name"
		chmod +x "$bin_dir/$name"
	done
}
