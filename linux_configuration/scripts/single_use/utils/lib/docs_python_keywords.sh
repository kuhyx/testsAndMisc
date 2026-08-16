#!/bin/bash
# Mapping Python keywords and operators to exact documentation anchors.
#
# Sourced by lookup_docs.sh; split out to keep docs_python.sh under the
# 250-line cap. Emits "<result>\t<desc>" so the caller keeps its own
# control flow; it reads doc_dir/term/term_lower from the caller's scope.

python_keyword_doc() {
	local doc_dir="$1" term="$2" term_lower="$3"
	local result="" desc=""

	#--------------------------------------------------------------------------
	# PRIORITY 1: Python keywords - map to exact documentation locations
	#--------------------------------------------------------------------------

	# Compound statements (reference/compound_stmts.html)
	case "$term_lower" in
	if | elif | else)
		result="$doc_dir/reference/compound_stmts.html#if"
		desc="Python: if statement"
		;;
	for)
		result="$doc_dir/reference/compound_stmts.html#for"
		desc="Python: for statement"
		;;
	while)
		result="$doc_dir/reference/compound_stmts.html#while"
		desc="Python: while statement"
		;;
	def)
		result="$doc_dir/reference/compound_stmts.html#def"
		desc="Python: function definition"
		;;
	class)
		result="$doc_dir/reference/compound_stmts.html#class"
		desc="Python: class definition"
		;;
	try | except | finally)
		result="$doc_dir/reference/compound_stmts.html#try"
		desc="Python: try statement"
		;;
	with)
		result="$doc_dir/reference/compound_stmts.html#with"
		desc="Python: with statement"
		;;
	async)
		result="$doc_dir/reference/compound_stmts.html#async"
		desc="Python: async definition"
		;;
	match | case)
		result="$doc_dir/reference/compound_stmts.html#match"
		desc="Python: match statement"
		;;
	esac

	# Simple statements (reference/simple_stmts.html)
	if [ -z "$result" ]; then
		case "$term_lower" in
		return)
			result="$doc_dir/reference/simple_stmts.html#return"
			desc="Python: return statement"
			;;
		pass)
			result="$doc_dir/reference/simple_stmts.html#pass"
			desc="Python: pass statement"
			;;
		break)
			result="$doc_dir/reference/simple_stmts.html#break"
			desc="Python: break statement"
			;;
		continue)
			result="$doc_dir/reference/simple_stmts.html#continue"
			desc="Python: continue statement"
			;;
		import | from)
			result="$doc_dir/reference/simple_stmts.html#import"
			desc="Python: import statement"
			;;
		raise)
			result="$doc_dir/reference/simple_stmts.html#raise"
			desc="Python: raise statement"
			;;
		assert)
			result="$doc_dir/reference/simple_stmts.html#assert"
			desc="Python: assert statement"
			;;
		yield)
			result="$doc_dir/reference/simple_stmts.html#yield"
			desc="Python: yield expression"
			;;
		del)
			result="$doc_dir/reference/simple_stmts.html#del"
			desc="Python: del statement"
			;;
		global)
			result="$doc_dir/reference/simple_stmts.html#global"
			desc="Python: global statement"
			;;
		nonlocal)
			result="$doc_dir/reference/simple_stmts.html#nonlocal"
			desc="Python: nonlocal statement"
			;;
		type)
			result="$doc_dir/reference/simple_stmts.html#type"
			desc="Python: type alias statement"
			;;
		esac
	fi

	# Expressions/operators (reference/expressions.html)
	if [ -z "$result" ]; then
		case "$term_lower" in
		and)
			result="$doc_dir/reference/expressions.html#and"
			desc="Python: and operator"
			;;
		or)
			result="$doc_dir/reference/expressions.html#or"
			desc="Python: or operator"
			;;
		not)
			result="$doc_dir/reference/expressions.html#not"
			desc="Python: not operator"
			;;
		in)
			result="$doc_dir/reference/expressions.html#in"
			desc="Python: in operator"
			;;
		is)
			result="$doc_dir/reference/expressions.html#is"
			desc="Python: is operator"
			;;
		lambda)
			result="$doc_dir/reference/expressions.html#lambda"
			desc="Python: lambda expression"
			;;
		await)
			result="$doc_dir/reference/expressions.html#await"
			desc="Python: await expression"
			;;
		esac
	fi

	# Built-in constants (library/constants.html) - case-sensitive!
	if [ -z "$result" ]; then
		case "$term" in
		True | False)
			result="$doc_dir/library/constants.html#$term"
			desc="Python: $term constant"
			;;
		None)
			result="$doc_dir/library/constants.html#None"
			desc="Python: None constant"
			;;
		Ellipsis)
			result="$doc_dir/library/constants.html#Ellipsis"
			desc="Python: Ellipsis constant"
			;;
		NotImplemented)
			result="$doc_dir/library/constants.html#NotImplemented"
			desc="Python: NotImplemented constant"
			;;
		esac
	fi

	printf '%s\t%s\n' "$result" "$desc"
}
