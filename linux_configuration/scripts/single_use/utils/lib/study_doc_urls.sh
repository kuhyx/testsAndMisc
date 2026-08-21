#!/usr/bin/env bash
# lib/study_doc_urls.sh — per-language documentation URL builders for the
# C-family, JS/TS and Python.
#
# Sourced by generate_study_materials.sh. Each takes a term and returns the
# canonical online doc URL for it, or an empty string when the language has no
# stable URL shape for that term.

# Python documentation
python_doc_url() {
	local term="$1"
	# Category (keyword, builtin, module), reserved for future use and never
	# read. Defaulted rather than required: get_doc_url has always called this
	# with one argument, which only worked because the entry script runs under
	# `set -e` without `-u`, so "$2" silently expanded to empty. Any caller that
	# does enable `set -u` -- a test, or a future lib that sources this -- would
	# otherwise abort here on an argument nothing uses.
	local _type="${2:-}"

	case "$term" in
	# Keywords
	if | else | elif | for | while | try | except | finally | with | as | import | from | def | class | return | yield | raise | pass | break | continue | and | or | not | in | is | lambda | global | nonlocal | assert | del | True | False | None | async | await)
		echo "https://docs.python.org/3/reference/compound_stmts.html"
		;;
	# Built-in functions
	print | len | range | type | str | int | float | list | dict | set | tuple | bool | open | input | format | sorted | reversed | enumerate | zip | map | filter | any | all | sum | min | max | abs | round | isinstance | issubclass | hasattr | getattr | setattr | delattr | callable | iter | next | super | property | staticmethod | classmethod | vars | dir | help | id | hash | repr | ascii | bin | hex | oct | chr | ord | eval | exec | compile)
		echo "https://docs.python.org/3/library/functions.html#$term"
		;;
	# Common modules
	os | sys | re | json | datetime | collections | itertools | functools | pathlib | subprocess | threading | multiprocessing | asyncio | typing | dataclasses | unittest | pytest | logging | argparse | configparser)
		echo "https://docs.python.org/3/library/$term.html"
		;;
	# Testing
	MagicMock | Mock | patch | PropertyMock)
		echo "https://docs.python.org/3/library/unittest.mock.html"
		;;
	*)
		echo "https://docs.python.org/3/search.html?q=$term"
		;;
	esac
}

# JavaScript/TypeScript documentation (MDN)
js_doc_url() {
	local term="$1"

	case "$term" in
	# Keywords & statements
	if | else | for | while | do | switch | case | break | continue | return | throw | try | catch | finally | function | class | const | let | var | new | this | super | import | export | default | async | await | yield | typeof | instanceof | in | of | delete | void)
		echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements"
		;;
	# Global objects
	Array | Object | String | Number | Boolean | Symbol | Map | Set | WeakMap | WeakSet | Date | RegExp | Error | Promise | Proxy | Reflect | JSON | Math | Intl)
		echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/$term"
		;;
	# Array methods
	map | filter | reduce | forEach | find | findIndex | some | every | includes | indexOf | slice | splice | concat | join | push | pop | shift | unshift | sort | reverse | flat | flatMap)
		echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/$term"
		;;
	# String methods
	split | replace | match | search | substring | substr | toLowerCase | toUpperCase | trim | padStart | padEnd | startsWith | endsWith | charAt | charCodeAt)
		echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/$term"
		;;
	# Promise methods
	then | resolve | reject | all | race | allSettled | any)
		echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/$term"
		;;
	# Common Web APIs
	fetch | console | document | window | localStorage | sessionStorage | setTimeout | setInterval | addEventListener | querySelector | querySelectorAll)
		echo "https://developer.mozilla.org/en-US/docs/Web/API"
		;;
	*)
		echo "https://developer.mozilla.org/en-US/search?q=$term"
		;;
	esac
}

# TypeScript-specific documentation
ts_doc_url() {
	local term="$1"

	case "$term" in
	interface | type | enum | namespace | declare | readonly | abstract | implements | extends | keyof | typeof | infer | as | is | asserts | satisfies | override)
		echo "https://www.typescriptlang.org/docs/handbook/2/everyday-types.html"
		;;
	Partial | Required | Readonly | Record | Pick | Omit | Exclude | Extract | NonNullable | ReturnType | Parameters | InstanceType | Awaited)
		echo "https://www.typescriptlang.org/docs/handbook/utility-types.html"
		;;
	*)
		# Fall back to JS docs for runtime features
		js_doc_url "$term"
		;;
	esac
}

# C documentation
c_doc_url() {
	local term="$1"

	case "$term" in
	# Keywords
	if | else | for | while | do | switch | case | break | continue | return | goto | sizeof | typedef | struct | union | enum | const | static | extern | register | volatile | inline | restrict | _Bool | _Complex | _Imaginary | _Alignas | _Alignof | _Atomic | _Generic | _Noreturn | _Static_assert | _Thread_local)
		echo "https://en.cppreference.com/w/c/keyword/$term"
		;;
	# Standard library headers
	stdio | stdlib | string | math | time | ctype | stdint | stdbool | stddef | limits | float | errno | assert | signal | setjmp | stdarg | locale)
		echo "https://en.cppreference.com/w/c/header/${term}.h"
		;;
	# Common functions
	printf | fprintf | sprintf | snprintf | scanf | fscanf | sscanf | fopen | fclose | fread | fwrite | fgets | fputs | fseek | ftell | rewind | fflush)
		echo "https://en.cppreference.com/w/c/io"
		;;
	malloc | calloc | realloc | free | memcpy | memmove | memset | memcmp)
		echo "https://en.cppreference.com/w/c/memory"
		;;
	strlen | strcpy | strncpy | strcat | strncat | strcmp | strncmp | strchr | strrchr | strstr | strtok)
		echo "https://en.cppreference.com/w/c/string/byte"
		;;
	*)
		echo "https://en.cppreference.com/mwiki/index.php?search=$term"
		;;
	esac
}

# C++ documentation
cpp_doc_url() {
	local term="$1"

	case "$term" in
	# C++ specific keywords
	class | public | private | protected | virtual | override | final | explicit | mutable | constexpr | consteval | constinit | concept | requires | co_await | co_yield | co_return | nullptr | noexcept | decltype | auto | template | typename | namespace | using | new | delete | throw | try | catch | static_cast | dynamic_cast | const_cast | reinterpret_cast)
		echo "https://en.cppreference.com/w/cpp/keyword/$term"
		;;
	# STL containers
	vector | list | deque | array | forward_list | set | map | unordered_set | unordered_map | multiset | multimap | stack | queue | priority_queue)
		echo "https://en.cppreference.com/w/cpp/container/$term"
		;;
	# STL algorithms
	sort | find | copy | move | transform | accumulate | count | remove | unique | reverse | rotate | shuffle | partition | merge | binary_search | lower_bound | upper_bound)
		echo "https://en.cppreference.com/w/cpp/algorithm/$term"
		;;
	# Smart pointers
	unique_ptr | shared_ptr | weak_ptr | make_unique | make_shared)
		echo "https://en.cppreference.com/w/cpp/memory/$term"
		;;
	# Common classes
	string | string_view | optional | variant | any | tuple | pair | function | bind | thread | mutex | future | promise | chrono)
		echo "https://en.cppreference.com/w/cpp/utility"
		;;
	*)
		# Try C docs as fallback
		c_doc_url "$term"
		;;
	esac
}
