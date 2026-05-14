#!/bin/bash
#==============================================================================
# Offline Documentation Lookup
# Searches downloaded documentation for terms
#
# Usage: ./lookup_docs.sh <term> [language] [--open] [--extract]
#
# Examples:
#   ./lookup_docs.sh Path python          # Find Path in Python docs
#   ./lookup_docs.sh vector c_cpp         # Find vector in C++ docs
#   ./lookup_docs.sh map                  # Find map in all languages
#   ./lookup_docs.sh --batch imports.txt  # Lookup multiple terms from file
#==============================================================================

set -e

# Configuration
DOCS_DIR="${OFFLINE_DOCS_DIR:-$HOME/.local/share/offline-docs}"
INDEX_DIR="$DOCS_DIR/.index"

# Colors - only use if stdout is a terminal
if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  BLUE='\033[0;34m'
  YELLOW='\033[1;33m'
  CYAN='\033[0;36m'
  NC='\033[0m'
else
  RED=''
  GREEN=''
  BLUE=''
  YELLOW=''
  CYAN=''
  NC=''
fi

#==============================================================================
# Python-specific lookup
#==============================================================================
lookup_python() {
  local term="$1"
  local in_module="$2" # Optional: look for term within this module
  local doc_dir="$DOCS_DIR/python"
  local result=""
  local desc=""

  # Normalize term (preserve case for True/False/None)
  local term_lower
  term_lower=$(echo "$term" | tr '[:upper:]' '[:lower:]')

  # If looking for a term within a specific module
  if [ -n "$in_module" ]; then
    local module_lower
    module_lower=$(echo "$in_module" | tr '[:upper:]' '[:lower:]')

    if [ -f "$doc_dir/library/${module_lower}.html" ]; then
      # Find anchor for the specific item in the module
      local anchor
      anchor=$(grep -oP "id=\"[^\"]*${term}[^\"]*\"" "$doc_dir/library/${module_lower}.html" 2> /dev/null | head -1 | sed 's/id="//;s/"//')

      if [ -n "$anchor" ]; then
        result="$doc_dir/library/${module_lower}.html#$anchor"
        desc="Python: $in_module.$term"
      else
        # Just link to the module
        result="$doc_dir/library/${module_lower}.html"
        desc="Python: $term in module $in_module"
      fi
      echo "$result|$desc"
      return 0
    fi
  fi

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

  # Verify file exists for keyword lookups
  if [ -n "$result" ] && [ ! -f "${result%%#*}" ]; then
    result=""
    desc=""
  fi

  #--------------------------------------------------------------------------
  # PRIORITY 2: Check if it's a module (pathlib, os, sys, etc.)
  #--------------------------------------------------------------------------
  if [ -z "$result" ] && [ -f "$doc_dir/library/${term_lower}.html" ]; then
    result="$doc_dir/library/${term_lower}.html"
    desc="Python module: $term"
  fi

  #--------------------------------------------------------------------------
  # PRIORITY 3: Built-in functions (library/functions.html)
  #--------------------------------------------------------------------------
  if [ -z "$result" ] && [ -f "$doc_dir/library/functions.html" ]; then
    if grep -q "id=\"$term_lower\"" "$doc_dir/library/functions.html" 2> /dev/null; then
      result="$doc_dir/library/functions.html#$term_lower"
      desc="Python built-in function: $term"
    fi
  fi

  #--------------------------------------------------------------------------
  # PRIORITY 4: Built-in types (library/stdtypes.html)
  #--------------------------------------------------------------------------
  if [ -z "$result" ]; then
    case "$term_lower" in
      str | string)
        result="$doc_dir/library/stdtypes.html#str"
        desc="Python: str type"
        ;;
      int | integer)
        result="$doc_dir/library/stdtypes.html#int"
        desc="Python: int type"
        ;;
      float)
        result="$doc_dir/library/stdtypes.html#float"
        desc="Python: float type"
        ;;
      list)
        result="$doc_dir/library/stdtypes.html#list"
        desc="Python: list type"
        ;;
      dict | dictionary)
        result="$doc_dir/library/stdtypes.html#dict"
        desc="Python: dict type"
        ;;
      set)
        result="$doc_dir/library/stdtypes.html#set"
        desc="Python: set type"
        ;;
      tuple)
        result="$doc_dir/library/stdtypes.html#tuple"
        desc="Python: tuple type"
        ;;
      bool | boolean)
        result="$doc_dir/library/stdtypes.html#boolean-values"
        desc="Python: bool type"
        ;;
      bytes)
        result="$doc_dir/library/stdtypes.html#bytes"
        desc="Python: bytes type"
        ;;
    esac
  fi

  #--------------------------------------------------------------------------
  # PRIORITY 5: Check for class/function in module docs (exact id match)
  #--------------------------------------------------------------------------
  if [ -z "$result" ]; then
    local found_in
    # Look for exact id match first
    found_in=$(grep -l "id=\"$term\"" "$doc_dir/library/"*.html 2> /dev/null | head -1)
    if [ -n "$found_in" ]; then
      result="$found_in#$term"
      local module
      module=$(basename "$found_in" .html)
      desc="Python: $term in module $module"
    fi
  fi

  #--------------------------------------------------------------------------
  # PRIORITY 6: Search in index
  #--------------------------------------------------------------------------
  if [ -z "$result" ] && [ -f "$INDEX_DIR/python_index.txt" ]; then
    local index_match
    index_match=$(grep -i "^$term " "$INDEX_DIR/python_index.txt" 2> /dev/null | head -1)
    if [ -n "$index_match" ]; then
      result=$(echo "$index_match" | cut -d' ' -f2-)
      desc="Python: $term (from index)"
    fi
  fi

  # NO full-text search fallback - it produces garbage results
  # If we can't find a specific doc, return nothing (will fall back to online)

  if [ -n "$result" ]; then
    echo "$result|$desc"
  fi
}

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
    found=$(find -L "$doc_dir" -name "*${term}*" -type f 2> /dev/null | head -1)
    if [ -n "$found" ]; then
      result="$found"
      desc="C/C++: $term"
    fi
  fi

  if [ -n "$result" ]; then
    echo "$result|$desc"
  fi
}

#==============================================================================
# JavaScript/MDN specific lookup
# Searches the cloned MDN content repository
#==============================================================================
lookup_js() {
  local term="$1"
  local mdn_dir="$DOCS_DIR/mdn-content/files/en-us"

  # Normalize term for searching
  local term_lower
  term_lower=$(echo "$term" | tr '[:upper:]' '[:lower:]')

  # Handle common statement aliases (MDN uses if...else, try...catch, etc.)
  local statement_aliases=(
    "if:if...else"
    "else:if...else"
    "try:try...catch"
    "catch:try...catch"
    "finally:try...catch"
    "do:do...while"
    "while:while"
    "for:for"
    "switch:switch"
    "case:switch"
    "default:switch"
  )

  for alias in "${statement_aliases[@]}"; do
    local key="${alias%%:*}"
    local value="${alias##*:}"
    if [ "$term_lower" = "$key" ]; then
      local stmt_dir="$mdn_dir/web/javascript/reference/statements/$value"
      if [ -d "$stmt_dir" ] && [ -f "$stmt_dir/index.md" ]; then
        local title
        title=$(grep -m1 "^title:" "$stmt_dir/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
        echo "$stmt_dir/index.md|${title:-$term}"
        return 0
      fi
    fi
  done

  # Handle boolean/null literals
  case "$term_lower" in
    true | false)
      local bool_dir="$mdn_dir/web/javascript/reference/global_objects/boolean"
      if [ -d "$bool_dir" ] && [ -f "$bool_dir/index.md" ]; then
        echo "$bool_dir/index.md|Boolean ($term)"
        return 0
      fi
      ;;
    null)
      local null_dir="$mdn_dir/web/javascript/reference/operators/null"
      if [ -d "$null_dir" ] && [ -f "$null_dir/index.md" ]; then
        local title
        title=$(grep -m1 "^title:" "$null_dir/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
        echo "$null_dir/index.md|${title:-null}"
        return 0
      fi
      ;;
    undefined)
      local undef_dir="$mdn_dir/web/javascript/reference/global_objects/undefined"
      if [ -d "$undef_dir" ] && [ -f "$undef_dir/index.md" ]; then
        local title
        title=$(grep -m1 "^title:" "$undef_dir/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
        echo "$undef_dir/index.md|${title:-undefined}"
        return 0
      fi
      ;;
  esac

  # Search JavaScript reference directory structure (priority order)
  local search_dirs=(
    "$mdn_dir/web/javascript/reference/statements"
    "$mdn_dir/web/javascript/reference/operators"
    "$mdn_dir/web/javascript/reference/global_objects"
    "$mdn_dir/web/javascript/reference/functions"
    "$mdn_dir/web/javascript/reference/classes"
  )

  for search_dir in "${search_dirs[@]}"; do
    if [ -d "$search_dir" ]; then
      # Look for exact directory match (MDN uses directories with index.md)
      local found_dir
      found_dir=$(find "$search_dir" -maxdepth 2 -type d -iname "$term" 2> /dev/null | head -1)
      if [ -n "$found_dir" ] && [ -f "$found_dir/index.md" ]; then
        local title
        title=$(grep -m1 "^title:" "$found_dir/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
        echo "$found_dir/index.md|${title:-$term}"
        return 0
      fi
    fi
  done

  # Search Web APIs - prioritize *_api directories for common terms
  if [ -d "$mdn_dir/web/api" ]; then
    # First try <term>_api directory (e.g., fetch_api, console_api)
    local api_dir="$mdn_dir/web/api/${term_lower}_api"
    if [ -d "$api_dir" ] && [ -f "$api_dir/index.md" ]; then
      local title
      title=$(grep -m1 "^title:" "$api_dir/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "$api_dir/index.md|${title:-$term API}"
      return 0
    fi

    # Then try exact top-level API interface (e.g., Console, Document, Element)
    local found
    found=$(find "$mdn_dir/web/api" -maxdepth 1 -type d -iname "$term" 2> /dev/null | head -1)
    if [ -n "$found" ] && [ -f "$found/index.md" ]; then
      local title
      title=$(grep -m1 "^title:" "$found/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "$found/index.md|${title:-$term}"
      return 0
    fi

    # Try window/<term> for global functions like alert, confirm, etc.
    local window_method="$mdn_dir/web/api/window/${term_lower}"
    if [ -d "$window_method" ] && [ -f "$window_method/index.md" ]; then
      local title
      title=$(grep -m1 "^title:" "$window_method/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "$window_method/index.md|${title:-Window.$term()}"
      return 0
    fi

    # Search nested API methods
    found=$(find "$mdn_dir/web/api" -maxdepth 3 -type d -iname "$term" 2> /dev/null | head -1)
    if [ -n "$found" ] && [ -f "$found/index.md" ]; then
      local title
      title=$(grep -m1 "^title:" "$found/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "$found/index.md|${title:-$term}"
      return 0
    fi
  fi

  # Now try partial matches in Global Objects (e.g., Array.from, Object.keys)
  if [ -d "$mdn_dir/web/javascript/reference/global_objects" ]; then
    local found
    found=$(find "$mdn_dir/web/javascript/reference/global_objects" -maxdepth 2 -type d -iname "*${term}*" 2> /dev/null | head -1)
    if [ -n "$found" ] && [ -f "$found/index.md" ]; then
      local title
      title=$(grep -m1 "^title:" "$found/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "$found/index.md|${title:-$term}"
      return 0
    fi
  fi

  # Glossary as last resort
  if [ -d "$mdn_dir/glossary" ]; then
    local found
    found=$(find "$mdn_dir/glossary" -maxdepth 1 -type d -iname "$term" 2> /dev/null | head -1)
    if [ -n "$found" ] && [ -f "$found/index.md" ]; then
      local title
      title=$(grep -m1 "^title:" "$found/index.md" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "$found/index.md|${title:-$term}"
      return 0
    fi
  fi

  return 1
}

#==============================================================================
# Rust specific lookup
#==============================================================================
lookup_rust() {
  local term="$1"
  local result=""
  local desc=""

  if command -v rustup &> /dev/null; then
    # Use rustup doc to get path
    local rust_doc_path
    rust_doc_path=$(rustup doc --path 2> /dev/null | head -1 | xargs dirname 2> /dev/null)

    # Search in std docs
    if [ -d "$rust_doc_path/std" ]; then
      local found
      found=$(find "$rust_doc_path/std" -name "*${term}*" -type f 2> /dev/null | head -1)
      if [ -n "$found" ]; then
        result="$found"
        desc="Rust: $term"
      fi
    fi
  fi

  if [ -n "$result" ]; then
    echo "$result|$desc"
  fi
}

#==============================================================================
# Go specific lookup
#==============================================================================
lookup_go() {
  local term="$1"
  local result=""
  local desc=""

  if command -v go &> /dev/null; then
    # Check if it's a stdlib package
    if go doc "$term" &> /dev/null; then
      result="go doc $term"
      desc="Go package: $term (use 'go doc $term' to view)"
    fi
  fi

  if [ -n "$result" ]; then
    echo "$result|$desc"
  fi
}

#==============================================================================
# Shell specific lookup
#==============================================================================
lookup_shell() {
  local term="$1"
  local doc_dir="$DOCS_DIR/shell"
  local result=""
  local desc=""

  # Check bash builtins
  if [ -f "$doc_dir/bash_builtins.txt" ]; then
    if grep -q "=== $term ===" "$doc_dir/bash_builtins.txt" 2> /dev/null; then
      result="$doc_dir/bash_builtins.txt"
      desc="Bash builtin: $term"
    fi
  fi

  # Check common commands
  if [ -z "$result" ] && [ -f "$doc_dir/common_commands.txt" ]; then
    if grep -q "^$term" "$doc_dir/common_commands.txt" 2> /dev/null; then
      local cmd_desc
      cmd_desc=$(grep "^$term" "$doc_dir/common_commands.txt" | head -1)
      result="$doc_dir/common_commands.txt"
      desc="Shell command: $cmd_desc"
    fi
  fi

  # Try man page
  if [ -z "$result" ]; then
    local man_path
    man_path=$(man -w "$term" 2> /dev/null)
    if [ -n "$man_path" ]; then
      result="man $term"
      desc="Manual page: $term (use 'man $term' to view)"
    fi
  fi

  if [ -n "$result" ]; then
    echo "$result|$desc"
  fi
}

#==============================================================================
# Generic lookup (searches all languages)
#==============================================================================
lookup_all() {
  local term="$1"

  # Try each language
  for lang in python cpp js rust go shell; do
    local result
    result=$(lookup_$lang "$term" 2> /dev/null)
    if [ -n "$result" ]; then
      echo "$lang: $result"
    fi
  done
}

#==============================================================================
# Parse Python import and lookup the actual imported item
#==============================================================================
parse_python_import() {
  local import_line="$1"

  # Handle "from X import Y" format
  if [[ $import_line =~ ^from[[:space:]]+([^[:space:]]+)[[:space:]]+import[[:space:]]+(.+) ]]; then
    local module="${BASH_REMATCH[1]}"
    local items="${BASH_REMATCH[2]}"

    # Clean up items (remove parentheses, commas, etc.)
    items=$(echo "$items" | sed 's/[(),]//g' | awk '{print $1}')

    # Output: module and first imported item
    echo "$module|$items"
    return 0
  fi

  # Handle "import X" format
  if [[ $import_line =~ ^import[[:space:]]+([^[:space:],]+) ]]; then
    local module="${BASH_REMATCH[1]}"
    echo "$module|"
    return 0
  fi

  return 1
}

#==============================================================================
# Smart lookup for imports
#==============================================================================
lookup_import() {
  local import_line="$1"
  local lang="$2"

  case "$lang" in
    python)
      local parsed
      parsed=$(parse_python_import "$import_line")
      if [ -n "$parsed" ]; then
        local module item
        module=$(echo "$parsed" | cut -d'|' -f1)
        item=$(echo "$parsed" | cut -d'|' -f2)

        # For "from X import Y", look up Y within module X's documentation
        if [ -n "$item" ] && [ -n "$module" ]; then
          local result
          # Pass both item and module to lookup_python
          result=$(lookup_python "$item" "$module")
          if [ -n "$result" ]; then
            echo "$result"
            return 0
          fi
        fi

        # Fall back to module documentation
        lookup_python "$module"
      fi
      ;;

    c_cpp)
      # Extract header name from #include <header> or #include "header"
      local header
      header=$(echo "$import_line" | sed -E 's/#include\s*[<"]([^">]+)[">]/\1/' | sed 's/\.h$//')
      lookup_cpp "$header"
      ;;

    javascript | typescript)
      # Extract module from import/require
      local module=""
      # Match: from "module" or from 'module'
      module=$(echo "$import_line" | grep -oP "from\s+['\"]\\K[^'\"]+")
      if [ -z "$module" ]; then
        # Match: require("module") or require('module')
        module=$(echo "$import_line" | grep -oP "require\\(['\"]\\K[^'\"]+")
      fi
      [ -n "$module" ] && lookup_js "$module"
      ;;

    *)
      echo "Unknown language: $lang"
      ;;
  esac
}

#==============================================================================
# Extract documentation content
#==============================================================================
extract_doc_content() {
  local file="$1"
  local term="$2"
  local max_lines="${3:-20}"

  if [[ $file == *.html ]]; then
    # Extract text from HTML, find section about term
    if command -v html2text &> /dev/null; then
      html2text "$file" 2> /dev/null | grep -A"$max_lines" -i "$term" | head -"$max_lines"
    elif command -v lynx &> /dev/null; then
      lynx -dump -nolist "$file" 2> /dev/null | grep -A"$max_lines" -i "$term" | head -"$max_lines"
    else
      # Basic extraction
      sed 's/<[^>]*>//g' "$file" | grep -A"$max_lines" -i "$term" | head -"$max_lines"
    fi
  elif [[ $file == *.json ]]; then
    # Pretty print JSON section
    grep -A5 "\"$term\"" "$file" 2> /dev/null
  else
    # Plain text
    grep -A"$max_lines" -i "$term" "$file" | head -"$max_lines"
  fi
}

#==============================================================================
# Main
#==============================================================================
usage() {
  cat << EOF
Usage: $0 <term> [language] [options]

Search offline documentation for a term.

Languages: python, cpp, c_cpp, js, javascript, rust, go, shell, all

Options:
    --open      Open the documentation file (requires xdg-open)
    --extract   Extract and display relevant content
    --import    Parse and lookup an import statement
    --batch     Process multiple terms from a file

Examples:
    $0 Path python                    # Find Path in Python docs
    $0 vector cpp                     # Find vector in C++ docs
    $0 map                            # Find map in all languages
    $0 --import "from pathlib import Path" python
    $0 --batch imports.txt python
EOF
}

main() {
  if [ $# -eq 0 ]; then
    usage
    exit 0
  fi

  local term=""
  local lang=""
  local action="lookup"
  local open_file=false
  local extract=false

  while [ $# -gt 0 ]; do
    case "$1" in
      --open)
        open_file=true
        shift
        ;;
      --extract)
        extract=true
        shift
        ;;
      --import)
        action="import"
        shift
        term="$1"
        shift
        ;;
      --batch)
        action="batch"
        shift
        term="$1" # This is the file
        shift
        ;;
      --help | -h)
        usage
        exit 0
        ;;
      python | cpp | c_cpp | c | js | javascript | ts | typescript | tsx | jsx | rust | go | shell | bash | all)
        lang="$1"
        shift
        ;;
      *)
        if [ -z "$term" ]; then
          term="$1"
        fi
        shift
        ;;
    esac
  done

  # Normalize language
  case "$lang" in
    c) lang="cpp" ;;
    javascript | js | typescript | ts | jsx | tsx) lang="js" ;;
    bash) lang="shell" ;;
    "") lang="all" ;;
  esac

  case "$action" in
    lookup)
      if [ "$lang" = "all" ]; then
        lookup_all "$term"
      else
        result=$(lookup_$lang "$term" 2> /dev/null)
        if [ -n "$result" ]; then
          local file desc
          file=$(echo "$result" | cut -d'|' -f1)
          desc=$(echo "$result" | cut -d'|' -f2)

          echo -e "${GREEN}Found:${NC} $desc"
          echo -e "${BLUE}File:${NC} $file"

          if $extract; then
            echo ""
            echo -e "${YELLOW}--- Content ---${NC}"
            extract_doc_content "$file" "$term"
          fi

          if $open_file && [ -f "$file" ]; then
            xdg-open "$file" 2> /dev/null &
          fi
        else
          echo -e "${RED}Not found:${NC} $term in $lang documentation"
        fi
      fi
      ;;

    import)
      result=$(lookup_import "$term" "$lang")
      if [ -n "$result" ]; then
        echo -e "${GREEN}Import lookup:${NC} $term"
        echo "$result"
      else
        echo -e "${RED}Could not parse import:${NC} $term"
      fi
      ;;

    batch)
      if [ ! -f "$term" ]; then
        echo "File not found: $term"
        exit 1
      fi

      while IFS= read -r line || [ -n "$line" ]; do
        [ -z "$line" ] && continue
        [[ $line =~ ^# ]] && continue

        echo -e "${CYAN}Looking up:${NC} $line"
        lookup_import "$line" "$lang"
        echo ""
      done < "$term"
      ;;
  esac
}

main "$@"
