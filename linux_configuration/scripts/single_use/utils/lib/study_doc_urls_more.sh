#!/usr/bin/env bash
# lib/study_doc_urls_more.sh — documentation URL builders for Rust, Go, Ruby,
# Java and shell.
#
# Split from study_doc_urls.sh purely to keep both files under the 250-line
# cap; the two are one subject and are always sourced together.

# Rust documentation
rust_doc_url() {
	local term="$1"

	case "$term" in
	# Keywords
	fn | let | mut | const | static | if | else | match | loop | while | for | in | break | continue | return | struct | enum | impl | trait | type | where | pub | mod | use | crate | self | super | async | await | move | ref | dyn | unsafe | extern)
		echo "https://doc.rust-lang.org/std/keyword.$term.html"
		;;
	# Common types
	Option | Result | Vec | String | Box | Rc | Arc | Cell | RefCell | Mutex | RwLock | HashMap | HashSet | BTreeMap | BTreeSet)
		echo "https://doc.rust-lang.org/std/$term"
		;;
	# Traits
	Clone | Copy | Debug | Default | Eq | PartialEq | Ord | PartialOrd | Hash | Display | From | Into | AsRef | AsMut | Deref | DerefMut | Iterator | IntoIterator | Send | Sync)
		echo "https://doc.rust-lang.org/std/$term"
		;;
	# Macros
	println | print | format | vec | panic | assert | assert_eq | assert_ne | debug_assert | todo | unimplemented | unreachable)
		echo "https://doc.rust-lang.org/std/macro.$term.html"
		;;
	*)
		echo "https://doc.rust-lang.org/std/?search=$term"
		;;
	esac
}

# Go documentation
go_doc_url() {
	local term="$1"

	case "$term" in
	# Keywords
	func | var | const | type | struct | interface | map | chan | go | select | defer | if | else | for | range | switch | case | default | break | continue | return | goto | fallthrough | package | import)
		echo "https://go.dev/ref/spec"
		;;
	# Built-in functions
	make | new | len | cap | append | copy | delete | close | panic | recover | print | println | complex | real | imag)
		echo "https://pkg.go.dev/builtin#$term"
		;;
	# Common packages
	fmt | os | io | net | http | json | time | strings | strconv | errors | context | sync | testing | reflect | regexp | sort | math | crypto | encoding | bufio | bytes | path | filepath)
		echo "https://pkg.go.dev/$term"
		;;
	*)
		echo "https://pkg.go.dev/search?q=$term"
		;;
	esac
}

# Ruby documentation
ruby_doc_url() {
	local term="$1"

	case "$term" in
	# Keywords
	if | else | elsif | unless | case | when | while | until | for | do | end | begin | rescue | ensure | raise | return | break | next | redo | retry | yield | def | class | module | self | super | nil | true | false | and | or | not | in | then | alias | defined | __FILE__ | __LINE__ | __ENCODING__)
		echo "https://ruby-doc.org/docs/keywords/1.9/"
		;;
	# Core classes
	String | Array | Hash | Integer | Float | Symbol | Range | Regexp | Time | Date | File | Dir | IO | Proc | Lambda | Method | Thread | Mutex | Fiber)
		echo "https://ruby-doc.org/core/classes/$term.html"
		;;
	# Enumerable methods
	each | map | select | reject | find | reduce | inject | collect | detect | sort | sort_by | group_by | partition | any | all | none | one | count | first | last | take | drop)
		echo "https://ruby-doc.org/core/Enumerable.html"
		;;
	*)
		echo "https://ruby-doc.org/search.html?q=$term"
		;;
	esac
}

# Java documentation
java_doc_url() {
	local term="$1"

	case "$term" in
	# Keywords
	if | else | for | while | do | switch | case | break | continue | return | throw | try | catch | finally | class | interface | enum | extends | implements | new | this | super | static | final | abstract | public | private | protected | void | null | true | false | instanceof | synchronized | volatile | transient | native | strictfp | assert | default | package | import)
		echo "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/"
		;;
	# Common classes
	String | Integer | Long | Double | Float | Boolean | Character | Object | Class | System | Math | Arrays | Collections | List | ArrayList | LinkedList | Map | HashMap | TreeMap | Set | HashSet | TreeSet | Queue | Stack | Optional | Stream)
		echo "https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/$term.html"
		;;
	*)
		echo "https://docs.oracle.com/en/java/javase/17/docs/api/search.html?q=$term"
		;;
	esac
}

# Shell documentation
shell_doc_url() {
	local term="$1"

	case "$term" in
	# Built-in commands
	if | then | else | elif | fi | for | while | until | do | done | case | 'esac' | in | function | select | time | coproc)
		echo "https://www.gnu.org/software/bash/manual/bash.html#Conditional-Constructs"
		;;
	echo | printf | read | declare | local | export | unset | set | shopt | alias | source | eval | exec | exit | return | break | continue | shift | trap | wait | kill | jobs | bg | fg | disown | suspend | logout | cd | pwd | pushd | popd | dirs | type | which | command | builtin | enable | help | hash | bind | complete | compgen | compopt)
		echo "https://www.gnu.org/software/bash/manual/bash.html#Shell-Builtin-Commands"
		;;
	# Common external commands
	grep | sed | awk | find | xargs | sort | uniq | cut | tr | head | tail | wc | cat | tee | diff | patch | tar | gzip | zip | curl | wget | ssh | scp | rsync | git | make | chmod | chown | chgrp | ln | cp | mv | rm | mkdir | rmdir | touch | ls | stat | file | df | du | free | top | ps | pkill | pgrep | nohup | screen | tmux)
		echo "https://man7.org/linux/man-pages/man1/$term.1.html"
		;;
	*)
		echo "https://www.gnu.org/software/bash/manual/bash.html"
		;;
	esac
}
