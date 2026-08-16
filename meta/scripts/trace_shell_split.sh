#!/usr/bin/env bash

# ============================================================================
# Capture an execution trace of a shell script with every mutating command
# stubbed, so a split can be verified by RUNNING it rather than by sourcing it.
#
# Why this exists: verify_shell_split.sh sources the libs and never calls them,
# which proves `source` lines resolve and nothing more. The analyze_repo.sh
# split passed that, plus bash -n, shellcheck and a function-set diff, and
# still shipped a script that aborted after language detection -- a `set -e`
# function-tail return and a self-referencing nameref, neither reachable
# without execution. See docs/shell-split-verification.md.
#
# The trace is the artifact: run this at the pre-split commit and again after
# the split, then diff. An identical trace means the same commands ran in the
# same order with the same arguments.
#
# Mutating binaries are shadowed by stubs earlier on PATH, so the live system
# is never touched. That is what makes this safe for the enforcement and
# installer scripts Decision 6 forbids executing for real.
#
# Usage:
#   trace_shell_split.sh <script> [-- <script args>]
#   trace_shell_split.sh <script> --out <file> [-- <script args>]
#   trace_shell_split.sh <script> --stub git,curl,makepkg --out <file>
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

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

TARGET=""
OUT=""
TEMP_DIR=""
declare -a SCRIPT_ARGS=()
declare -a EXTRA_STUBS=()

cleanup() {
	if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
		rm -rf "$TEMP_DIR"
	fi
}

trap cleanup EXIT

usage() {
	echo "Usage: $SCRIPT_NAME <script> [--out <file>] [--stub a,b] [-- <script args>]"
	echo "  <script>      script to trace (not modified)"
	echo "  --out <file>  write the trace here (default: stdout)"
	echo "  --stub a,b    also shadow these binaries (e.g. git,curl,makepkg)"
	echo "  --            everything after this is passed to the script"
	exit 0
}

validate_requirements() {
	if [[ -z "$TARGET" ]]; then
		echo "Error: no script given" >&2
		exit 1
	fi
	if [[ ! -f "$TARGET" ]]; then
		echo "Error: no such script: $TARGET" >&2
		exit 1
	fi
}

# One stub per mutating command: append the call to the trace, succeed.
# Stubs report success because the point is to reach later code paths, not to
# simulate failure. A script whose logic branches on a real exit status needs a
# hand-written stub instead -- note that in the split's evidence file.
write_stubs() {
	local bin_dir="$1" name
	mkdir -p "$bin_dir"
	for name in "${DEFAULT_STUBBED_COMMANDS[@]}" ${EXTRA_STUBS[@]+"${EXTRA_STUBS[@]}"}; do
		cat >"$bin_dir/$name" <<STUB
#!/usr/bin/env bash
printf '%s %s\n' "$name" "\$*" >>"\$TRACE_FILE"
exit 0
STUB
		chmod +x "$bin_dir/$name"
	done
}

main() {
	validate_requirements

	TEMP_DIR="$(mktemp -d)"
	if [[ ! -d "$TEMP_DIR" ]]; then
		echo "Error: failed to create temporary directory" >&2
		exit 1
	fi

	local bin_dir="$TEMP_DIR/bin"
	local trace="$TEMP_DIR/trace.txt"
	: >"$trace"
	write_stubs "$bin_dir"

	# xtrace to a dedicated fd so the script's own stdout stays separate.
	local xtrace="$TEMP_DIR/xtrace.txt"

	set +e
	(
		export TRACE_FILE="$trace"
		export PATH="$bin_dir:$PATH"
		# A stubbed run must never believe it is root.
		export EUID_OVERRIDE=1000
		exec 9>"$xtrace"
		export BASH_XTRACEFD=9
		set -x
		bash "$TARGET" "${SCRIPT_ARGS[@]+"${SCRIPT_ARGS[@]}"}"
	) >"$TEMP_DIR/stdout.txt" 2>"$TEMP_DIR/stderr.txt"
	local status=$?
	set -e

	{
		echo "=== exit status: $status"
		echo "=== mutating calls (stubbed)"
		cat "$trace"
		echo "=== stdout"
		cat "$TEMP_DIR/stdout.txt"
		echo "=== stderr"
		cat "$TEMP_DIR/stderr.txt"
	} >"${OUT:-/dev/stdout}"
}

while [[ $# -gt 0 ]]; do
	case $1 in
	--out)
		OUT="$2"
		shift 2
		;;
	--stub)
		# Comma-separated extra binaries to shadow for this run only.
		IFS=',' read -r -a EXTRA_STUBS <<<"$2"
		shift 2
		;;
	-h | --help)
		usage
		;;
	--)
		shift
		SCRIPT_ARGS=("$@")
		break
		;;
	*)
		if [[ -z "$TARGET" ]]; then
			TARGET="$1"
			shift
		else
			echo "Unknown option: $1" >&2
			exit 1
		fi
		;;
	esac
done

main "$@"
