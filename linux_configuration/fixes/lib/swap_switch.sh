#!/bin/bash
# Shared by setup_zram.sh and setup_zswap.sh: the zswap kernel-cmdline edit,
# the "can zram drain into RAM" guard, and the live zswap parameters.
#
# Sourced, not run; the caller sets SS_NAME (its prefix in messages). Every
# system path has an env override so the tests in lib/tests run against a
# fixture tree and never touch /boot, /etc or /sys.

readonly LOADER_ENTRIES_DIR="${LOADER_ENTRIES_DIR:-/boot/loader/entries}"
readonly GRUB_DEFAULT_FILE="${GRUB_DEFAULT_FILE:-/etc/default/grub}"
readonly GRUB_CFG_FILE="${GRUB_CFG_FILE:-/boot/grub/grub.cfg}"
readonly ZSWAP_PARAMS_DIR="${ZSWAP_PARAMS_DIR:-/sys/module/zswap/parameters}"
readonly ZRAM_SYSFS="${ZRAM_SYSFS:-/sys/block/zram0}"
readonly PROC_MEMINFO="${PROC_MEMINFO:-/proc/meminfo}"
readonly SWAP_SWITCH_BACKUP_DIR="${SWAP_SWITCH_BACKUP_DIR:-/var/lib/swap-switch}"
readonly ZRAM_DEV=/dev/zram0
readonly SS_MIN_SPARE_KIB=$((2 * 1024 * 1024)) # keep 2 GiB free after swapoff

ss_die() {
	echo "${SS_NAME}: $*" >&2
	exit 1
}

# ss_reboot_to_apply REASON — the boot config is already written; the live
# switch is not safe now. Exit 3 is the documented "reboot to apply" code.
ss_reboot_to_apply() {
	echo "${SS_NAME}: $1; boot config is updated, reboot to apply" >&2
	exit 3
}

as_root() {
	if [[ $EUID -eq 0 ]]; then "$@"; else sudo -n "$@"; fi
}

ss_zram_active() {
	swapon --noheadings --show=NAME | grep -qx "$ZRAM_DEV"
}

# ss_has_disk_swap — any active swap that is not zram (zswap needs one).
ss_has_disk_swap() {
	swapon --noheadings --show=NAME | grep -qvx "$ZRAM_DEV"
}

# ss_can_drain — 0 when MemAvailable absorbs the zram contents with 2 GiB
# spare. The cost is the uncompressed data minus the compressed pages that
# swapoff frees as it drains; disk swap is NOT a swapoff target.
ss_can_drain() {
	local orig total avail
	read -r orig total < <(zramctl --bytes --noheadings --raw -o DATA,TOTAL "$ZRAM_DEV")
	avail=$(awk '/^MemAvailable:/ {print $2}' "$PROC_MEMINFO")
	((avail - (orig - total) / 1024 >= SS_MIN_SPARE_KIB))
}

# ss_edit_tokens TOKENS — filter stdin: drop every zswap.* word of a kernel
# cmdline and put TOKENS where the first one stood (appended if none). Words
# are space-separated; a leading key such as `options` is just a word.
ss_edit_tokens() {
	local tokens="$1" word out placed=0
	local -a words
	read -r -a words
	for word in "${words[@]}"; do
		if [[ $word == zswap.* ]]; then
			((placed)) || [[ -z $tokens ]] || out+=" ${tokens}"
			placed=1
		else
			out+=" ${word}"
		fi
	done
	((placed)) || [[ -z $tokens ]] || out+=" ${tokens}"
	printf '%s\n' "${out# }"
}

# _ss_rewrite FILE KIND TOKENS — rewrite FILE's cmdline line(s); print
# "changed" when the content differs (and is then installed with a one-time
# backup of the original), nothing otherwise.
_ss_rewrite() {
	local file="$1" kind="$2" tokens="$3" line tmp edited=0
	tmp="$(mktemp)"
	while IFS= read -r line || [[ -n $line ]]; do
		if [[ $kind == loader && $line == options\ * ]] && ((! edited)); then
			line="$(ss_edit_tokens "$tokens" <<<"$line")"
			edited=1
		elif [[ $kind == loader && $line == options\ * ]]; then
			line="$(ss_edit_tokens "" <<<"$line")"
		elif [[ $kind == grub && $line =~ ^GRUB_CMDLINE_LINUX_DEFAULT=\"(.*)\"$ ]]; then
			line="GRUB_CMDLINE_LINUX_DEFAULT=\"$(ss_edit_tokens "$tokens" <<<"${BASH_REMATCH[1]}")\""
		fi
		printf '%s\n' "$line"
	done <"$file" >"$tmp"
	if cmp -s "$file" "$tmp"; then
		rm -f "$tmp"
		return 0
	fi
	local backup
	backup="${SWAP_SWITCH_BACKUP_DIR}/$(basename "$file").orig"
	as_root mkdir -p "$SWAP_SWITCH_BACKUP_DIR"
	[[ -e $backup ]] || as_root cp -p "$file" "$backup"
	as_root install -m 644 "$tmp" "$file"
	rm -f "$tmp"
	echo changed
}

# _ss_zswap_words — filter stdin: print a cmdline's zswap.* words, in order.
# Splits on spaces and tabs, so a grub.cfg `linux` line works as is.
_ss_zswap_words() {
	local word out=""
	local -a words
	read -r -a words
	for word in "${words[@]}"; do
		if [[ $word == zswap.* ]]; then out+=" ${word}"; fi
	done
	printf '%s\n' "${out# }"
}

# _ss_grub_cfg_problem TOKENS — print why grub.cfg would not boot TOKENS;
# nothing when it would. Every `linux` line with zswap.* words must carry
# exactly TOKENS and at least one must: a recovery line, built from
# GRUB_CMDLINE_LINUX alone, carries none. Read as root: grub.cfg can be 600.
_ss_grub_cfg_problem() {
	local tokens="$1" cfg line words matched=0
	if ! cfg="$(as_root cat "$GRUB_CFG_FILE" 2>/dev/null)"; then
		echo "$GRUB_CFG_FILE is missing"
		return 0
	fi
	while IFS= read -r line; do
		[[ $line =~ ^[[:space:]]*linux[[:space:]] ]] || continue
		words="$(_ss_zswap_words <<<"$line")"
		[[ -n $words ]] || continue
		if [[ $words != "$tokens" ]]; then
			printf 'this line boots "%s": %s\n' "$words" "${line#"${line%%[![:space:]]*}"}"
			return 0
		fi
		matched=1
	done <<<"$cfg"
	((matched)) || echo "no linux line in $GRUB_CFG_FILE carries $tokens"
}

# _ss_set_grub TOKENS — GRUB's defaults, then grub.cfg: rebuilt when the
# defaults changed OR it does not boot TOKENS yet. The second case heals a
# run cut off between the two writes, which left the defaults right and
# grub.cfg on the old setup. Prints "changed" when it wrote anything.
_ss_set_grub() {
	local tokens="$1" changed log problem
	changed="$(_ss_rewrite "$GRUB_DEFAULT_FILE" grub "$tokens")"
	[[ -n $changed || -n $(_ss_grub_cfg_problem "$tokens") ]] || return 0
	# grub-mkconfig narrates every step on stderr; show it only on failure.
	log="$(as_root grub-mkconfig -o "$GRUB_CFG_FILE" 2>&1)" ||
		ss_die "grub-mkconfig failed: $log"
	problem="$(_ss_grub_cfg_problem "$tokens")"
	[[ -z $problem ]] || ss_die "grub.cfg still wrong after grub-mkconfig, $problem" \
		"(zswap.* words belong only in GRUB_CMDLINE_LINUX_DEFAULT; check GRUB_CMDLINE_LINUX in $GRUB_DEFAULT_FILE)"
	echo changed
}

# ss_set_boot_tokens TOKENS — persist the zswap.* words for the next boot:
# every systemd-boot entry when there are any, else GRUB. Other words,
# resume= included, stay. Exits 1 when the next boot would still not carry
# TOKENS, before the caller touches any live swap.
ss_set_boot_tokens() {
	local tokens="$1" entry changed="" bad=""
	local -a entries=()
	if [[ -d $LOADER_ENTRIES_DIR ]]; then
		mapfile -t entries < <(find "$LOADER_ENTRIES_DIR" -maxdepth 1 -name '*.conf' | sort)
	fi
	if ((${#entries[@]})); then
		for entry in "${entries[@]}"; do
			changed+="$(_ss_rewrite "$entry" loader "$tokens")"
			[[ $(grep '^options ' "$entry" | tr '\n' ' ' | _ss_zswap_words) == "$tokens" ]] ||
				bad+=" $(basename "$entry")"
		done
		[[ -z $bad ]] || ss_die "no options line carrying \"$tokens\" in${bad} ($LOADER_ENTRIES_DIR); fix the entry by hand"
	elif [[ -f $GRUB_DEFAULT_FILE ]]; then
		changed="$(_ss_set_grub "$tokens")"
	else
		ss_die "no systemd-boot entries in $LOADER_ENTRIES_DIR and no $GRUB_DEFAULT_FILE"
	fi
	[[ -z $changed ]] || echo "${SS_NAME}: kernel cmdline now carries: $tokens"
}

# ss_zswap_set NAME VALUE — write a live zswap parameter when it differs.
ss_zswap_set() {
	local path="${ZSWAP_PARAMS_DIR}/$1"
	[[ $(cat "$path") == "$2" ]] && return 0
	printf '%s\n' "$2" | as_root tee "$path" >/dev/null
}

ss_report() {
	swapon --show
	local p
	for p in enabled compressor max_pool_percent shrinker_enabled; do
		printf 'zswap %s=%s\n' "$p" "$(cat "${ZSWAP_PARAMS_DIR}/$p")"
	done
}
