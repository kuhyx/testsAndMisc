#!/bin/bash
# Shell-file discovery (git-tracked where possible, else a filesystem walk,
# matching by extension or shebang) and the file listing.
#
# Sourced by shell_check.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's options and reads the
# ABS_FILES_Z / REL_FILES_Z paths the entry sets above the source line.

discover_shell_files() {
	local base="$1"
	local -a all
	all=()

	if git -C "$base" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		while IFS= read -r -d '' f; do all+=("$f"); done < <(git -C "$base" ls-files -z)
		while IFS= read -r -d '' f; do all+=("$f"); done < <(git -C "$base" ls-files --others --exclude-standard -z)
	else
		while IFS= read -r -d '' f; do
			# trim leading ./ to keep consistent style with git paths
			f="${f#./}"
			f="${f#"${base}"/}"
			all+=("$f")
		done < <(find "$base" -type f -print0)
	fi

	local -a shells
	shells=()

	for rel in "${all[@]}"; do
		# skip binary-ish or huge files quickly by extension heuristic
		case "$rel" in
		*.png | *.jpg | *.jpeg | *.gif | *.ico | *.pdf | *.svg | *.zip | *.tar | *.gz | *.xz | *.7z | *.so | *.o | *.bin)
			continue
			;;
		esac

		local abs="$base/$rel"
		[[ -f $abs && -r $abs ]] || continue

		if [[ $rel == *.sh || $rel == *.bash || $rel == *.zsh ]]; then
			shells+=("$rel")
			continue
		fi

		# Check shebang
		local first
		first=$(head -n 1 -- "$abs" 2>/dev/null || true)
		if [[ $first =~ ^#! && $first =~ (ba|z|d|k)?sh ]]; then
			shells+=("$rel")
			continue
		fi

		# Also catch executable files with shell shebang even without extension
		if [[ -x $abs ]]; then
			if [[ $first =~ ^#! && $first =~ (ba|z|d|k)?sh ]]; then
				shells+=("$rel")
			fi
		fi
	done

	# write lists
	: >"$REL_FILES_Z"
	: >"$ABS_FILES_Z"
	for rel in "${shells[@]}"; do
		printf '%s\0' "$rel" >>"$REL_FILES_Z"
		printf '%s\0' "$base/$rel" >>"$ABS_FILES_Z"
	done
}

print_file_list() {
	local count
	count=$(tr -cd '\0' <"$REL_FILES_Z" | wc -c)
	log_info "Discovered $count shell file(s) under $ROOT_DIR"
	if [[ $VERBOSE == "true" ]]; then
		tr '\0' '\n' <"$REL_FILES_Z" | sed 's/^/  - /'
	fi
}
