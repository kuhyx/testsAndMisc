#!/bin/bash
# The linter runs themselves: shellcheck, shfmt diff mode, the optional
# checkbashisms and bashate passes, and the per-dialect syntax checks.
#
# Sourced by shell_check.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's options and reads
# TMPDIR, ABS_FILES_Z and VERBOSE, which the entry sets above the source line.

run_linters() {
	local issues=0
	local count
	count=$(tr -cd '\0' <"$ABS_FILES_Z" | wc -c)
	if [[ $count -eq 0 ]]; then
		log_warn "No shell files found to lint."
		return 0
	fi

	mapfile -d '' -t FILES <"$ABS_FILES_Z"

	log_info "Running shellcheck..."
	local sc_out="$TMPDIR/shellcheck.txt"
	if is_cmd shellcheck; then
		if ! shellcheck -x -S style "${FILES[@]}" >"$sc_out" 2>&1; then
			issues=$((issues + 1))
		fi
	else
		log_warn "shellcheck not found; skipping"
	fi

	log_info "Running shfmt (diff mode)..."
	local shfmt_out="$TMPDIR/shfmt.diff"
	if is_cmd shfmt; then
		if ! shfmt -d -i 2 -ci -sr -s "${FILES[@]}" >"$shfmt_out" 2>&1; then
			# shfmt returns non-zero when diff exists
			issues=$((issues + 1))
		fi
	else
		log_warn "shfmt not found; skipping"
	fi

	log_info "Running checkbashisms (optional)..."
	local cbi_out="$TMPDIR/checkbashisms.txt"
	local cbi_status=0
	if is_cmd checkbashisms; then
		# Only run checkbashisms on scripts that are intended for /bin/sh (or unspecified),
		# skip explicit bash/zsh scripts to avoid false positives.
		local -a CBI_FILES
		CBI_FILES=()
		for f in "${FILES[@]}"; do
			local first
			first=$(head -n 1 -- "$f" 2>/dev/null || true)
			if [[ $first =~ bash || $first =~ zsh ]]; then
				continue
			fi
			CBI_FILES+=("$f")
		done
		if [[ ${#CBI_FILES[@]} -gt 0 ]]; then
			# checkbashisms exits 0 if OK, 1 if issues, other codes for tool warnings
			checkbashisms "${CBI_FILES[@]}" >"$cbi_out" 2>&1
		else
			: >"$cbi_out"
		fi
		cbi_status=$?
		if [[ $cbi_status -eq 1 ]]; then
			issues=$((issues + 1))
		elif [[ $cbi_status -ne 0 ]]; then
			log_warn "checkbashisms exited with status $cbi_status (treated as warning)"
		fi
	else
		log_warn "checkbashisms not found; skipping"
	fi

	log_info "Running bash/zsh/sh syntax checks (-n)..."
	local bash_out="$TMPDIR/bash_syntax.txt"
	local zsh_out="$TMPDIR/zsh_syntax.txt"
	local sh_out="$TMPDIR/sh_syntax.txt"

	# Partition files by shebang for better accuracy
	local -a BASH_FILES ZSH_FILES SH_FILES
	BASH_FILES=()
	ZSH_FILES=()
	SH_FILES=()
	for f in "${FILES[@]}"; do
		local first
		first=$(head -n 1 -- "$f" 2>/dev/null || true)
		if [[ $first =~ bash ]]; then
			BASH_FILES+=("$f")
		elif [[ $first =~ zsh ]]; then
			ZSH_FILES+=("$f")
		else
			SH_FILES+=("$f")
		fi
	done

	if [[ ${#BASH_FILES[@]} -gt 0 ]] && is_cmd bash; then
		if ! bash -n "${BASH_FILES[@]}" 2>"$bash_out"; then
			issues=$((issues + 1))
		fi
	fi
	if [[ ${#ZSH_FILES[@]} -gt 0 ]] && is_cmd zsh; then
		if ! zsh -n "${ZSH_FILES[@]}" 2>"$zsh_out"; then
			issues=$((issues + 1))
		fi
	fi
	# prefer dash if present for /bin/sh style
	if [[ ${#SH_FILES[@]} -gt 0 ]]; then
		if is_cmd dash; then
			if ! dash -n "${SH_FILES[@]}" 2>"$sh_out"; then
				issues=$((issues + 1))
			fi
		elif is_cmd sh; then
			if ! sh -n "${SH_FILES[@]}" 2>"$sh_out"; then
				issues=$((issues + 1))
			fi
		fi
	fi

	echo
	log_info "========== Shell Lint Report =========="

	if [[ -s $sc_out ]]; then
		printf '\n\033[1m-- shellcheck --\033[0m\n'
		cat "$sc_out"
	else
		printf '\n\033[1;32m-- shellcheck: PASS (no issues) --\033[0m\n'
	fi

	if [[ -s $shfmt_out ]]; then
		printf '\n\033[1m-- shfmt (diffs found) --\033[0m\n'
		cat "$shfmt_out"
	else
		printf '\n\033[1;32m-- shfmt: PASS (formatted) --\033[0m\n'
	fi

	if [[ -s $cbi_out ]]; then
		printf '\n\033[1m-- checkbashisms --\033[0m\n'
		cat "$cbi_out"
	else
		printf '\n\033[1;32m-- checkbashisms: PASS (or skipped) --\033[0m\n'
	fi

	if [[ -s $bash_out ]]; then
		printf '\n\033[1m-- bash -n (syntax) --\033[0m\n'
		cat "$bash_out"
	else
		printf '\n\033[1;32m-- bash -n: PASS (or none) --\033[0m\n'
	fi

	if [[ -s $zsh_out ]]; then
		printf '\n\033[1m-- zsh -n (syntax) --\033[0m\n'
		cat "$zsh_out"
	else
		printf '\n\033[1;32m-- zsh -n: PASS (or none) --\033[0m\n'
	fi

	if [[ -s $sh_out ]]; then
		printf '\n\033[1m-- sh/dash -n (syntax) --\033[0m\n'
		cat "$sh_out"
	else
		printf '\n\033[1;32m-- sh/dash -n: PASS (or none) --\033[0m\n'
	fi

	echo
	if [[ $issues -gt 0 ]]; then
		log_error "Linting completed with $issues tool(s) reporting issues."
		return 1
	else
		log_info "All checks passed."
		return 0
	fi
}
