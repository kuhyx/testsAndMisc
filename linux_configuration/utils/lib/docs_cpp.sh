#!/bin/bash
# C++ documentation lookup.
#
# Sourced by lookup_docs.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

#==============================================================================
# C/C++ specific lookup
#==============================================================================
lookup_cpp() {
	local term="$1"
	local doc_dir="$DOCS_DIR/c_cpp"
	local result=""
	local desc=""

	# Resolve symlink if present (system package installs to c_cpp/system/)
	[ -L "$doc_dir/system" ] && doc_dir="$doc_dir/system"

	# Common C headers
	case "$term" in
	stdio.h | stdio)
		[ -f "$doc_dir/reference/cstdio/index.html" ] && result="$doc_dir/reference/cstdio/index.html"
		[ -f "$doc_dir/en/c/io.html" ] && result="$doc_dir/en/c/io.html"
		desc="C standard I/O header"
		;;
	stdlib.h | stdlib)
		[ -f "$doc_dir/reference/cstdlib/index.html" ] && result="$doc_dir/reference/cstdlib/index.html"
		[ -f "$doc_dir/en/c/memory.html" ] && result="$doc_dir/en/c/memory.html"
		desc="C standard library header"
		;;
	string.h | cstring)
		[ -f "$doc_dir/reference/cstring/index.html" ] && result="$doc_dir/reference/cstring/index.html"
		desc="C string handling header"
		;;
	math.h | cmath)
		[ -f "$doc_dir/reference/cmath/index.html" ] && result="$doc_dir/reference/cmath/index.html"
		desc="C math header"
		;;
	esac

	# C++ STL containers
	case "$term" in
	vector)
		[ -f "$doc_dir/reference/vector/index.html" ] && result="$doc_dir/reference/vector/index.html"
		[ -f "$doc_dir/en/cpp/container/vector.html" ] && result="$doc_dir/en/cpp/container/vector.html"
		desc="C++ std::vector container"
		;;
	map)
		[ -f "$doc_dir/reference/map/index.html" ] && result="$doc_dir/reference/map/index.html"
		desc="C++ std::map container"
		;;
	string)
		[ -f "$doc_dir/reference/string/index.html" ] && result="$doc_dir/reference/string/index.html"
		desc="C++ std::string"
		;;
	iostream)
		[ -f "$doc_dir/reference/iostream/index.html" ] && result="$doc_dir/reference/iostream/index.html"
		desc="C++ iostream header"
		;;
	esac

	# C keywords
	case "$term" in
	if | else | for | while | do | switch | case | break | continue | return | goto)
		[ -f "$doc_dir/en/c/language/$term.html" ] && result="$doc_dir/en/c/language/$term.html"
		[ -f "$doc_dir/en/cpp/language/$term.html" ] && result="$doc_dir/en/cpp/language/$term.html"
		desc="C/C++ keyword: $term"
		;;
	int | char | float | double | void | long | short | unsigned | signed)
		[ -f "$doc_dir/en/c/language/type.html" ] && result="$doc_dir/en/c/language/type.html"
		desc="C/C++ type: $term"
		;;
	struct | union | enum | typedef)
		[ -f "$doc_dir/en/c/language/$term.html" ] && result="$doc_dir/en/c/language/$term.html"
		desc="C/C++ keyword: $term"
		;;
	esac

	# Search in files if not found (use -L to follow symlinks)
	if [ -z "$result" ]; then
		local found
		found=$(find -L "$doc_dir" -name "*${term}*" -type f 2>/dev/null | head -1)
		if [ -n "$found" ]; then
			result="$found"
			desc="C/C++: $term"
		fi
	fi

	if [ -n "$result" ]; then
		echo "$result|$desc"
	fi
}
