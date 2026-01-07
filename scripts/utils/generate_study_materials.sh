#!/bin/bash
# Generate study materials (documentation links + Anki cards) from repo analysis
# Usage: ./generate_study_materials.sh <results_dir> [--top N] [--languages "python,c,js"]
#
# Examples:
#   ./generate_study_materials.sh /tmp/repo_analysis/results_myproject
#   ./generate_study_materials.sh /tmp/repo_analysis/results_linux --top 20 --languages "c"
#   ./generate_study_materials.sh ./results --languages "python,typescript"

set -e

#==============================================================================
# Configuration
#==============================================================================
RESULTS_DIR="${1:-.}"
TOP_N=30
LANGUAGES="auto"  # Will detect from results

# Parse arguments
shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --top)
            TOP_N="$2"
            shift 2
            ;;
        --languages)
            LANGUAGES="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Output files
DOCS_FILE="$RESULTS_DIR/documentation_links.md"
ANKI_FILE="$RESULTS_DIR/anki_cards.txt"
LLM_PROMPT_FILE="$RESULTS_DIR/llm_anki_prompt.md"

# Offline documentation setup
OFFLINE_DOCS_DIR="${OFFLINE_DOCS_DIR:-$HOME/.local/share/offline-docs}"
LOOKUP_SCRIPT="$(dirname "$0")/lookup_docs.sh"
USE_OFFLINE_DOCS=false

# Check if offline docs are available
if [ -d "$OFFLINE_DOCS_DIR" ] && [ -x "$LOOKUP_SCRIPT" ]; then
    USE_OFFLINE_DOCS=true
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

#==============================================================================
# Offline Documentation Lookup (preferred if available)
#==============================================================================
lookup_offline() {
    local term="$1"
    local lang="$2"
    local import_line="$3"  # Optional: full import line for context
    
    if ! $USE_OFFLINE_DOCS; then
        return 1
    fi
    
    local result
    if [ -n "$import_line" ]; then
        # Use import-aware lookup - get the line with the file path
        result=$("$LOOKUP_SCRIPT" --import "$import_line" "$lang" 2>/dev/null | grep "^/" | head -1)
    else
        result=$("$LOOKUP_SCRIPT" "$term" "$lang" 2>/dev/null | grep "^File:" | head -1 | sed 's/^File: //')
    fi
    
    if [ -n "$result" ]; then
        # Extract file path (before the | separator)
        local file_path
        file_path=$(echo "$result" | cut -d'|' -f1)
        if [ -n "$file_path" ]; then
            echo "$file_path"
            return 0
        fi
    fi
    
    return 1
}

#==============================================================================
# Documentation URL Generators (online fallback)
#==============================================================================

# Python documentation
python_doc_url() {
    local term="$1"
    local type="$2"  # keyword, builtin, module
    
    case "$term" in
        # Keywords
        if|else|elif|for|while|try|except|finally|with|as|import|from|def|class|return|yield|raise|pass|break|continue|and|or|not|in|is|lambda|global|nonlocal|assert|del|True|False|None|async|await)
            echo "https://docs.python.org/3/reference/compound_stmts.html"
            ;;
        # Built-in functions
        print|len|range|type|str|int|float|list|dict|set|tuple|bool|open|input|format|sorted|reversed|enumerate|zip|map|filter|any|all|sum|min|max|abs|round|isinstance|issubclass|hasattr|getattr|setattr|delattr|callable|iter|next|super|property|staticmethod|classmethod|vars|dir|help|id|hash|repr|ascii|bin|hex|oct|chr|ord|eval|exec|compile)
            echo "https://docs.python.org/3/library/functions.html#$term"
            ;;
        # Common modules
        os|sys|re|json|datetime|collections|itertools|functools|pathlib|subprocess|threading|multiprocessing|asyncio|typing|dataclasses|unittest|pytest|logging|argparse|configparser)
            echo "https://docs.python.org/3/library/$term.html"
            ;;
        # Testing
        MagicMock|Mock|patch|PropertyMock)
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
        if|else|for|while|do|switch|case|break|continue|return|throw|try|catch|finally|function|class|const|let|var|new|this|super|import|export|default|async|await|yield|typeof|instanceof|in|of|delete|void)
            echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements"
            ;;
        # Global objects
        Array|Object|String|Number|Boolean|Symbol|Map|Set|WeakMap|WeakSet|Date|RegExp|Error|Promise|Proxy|Reflect|JSON|Math|Intl)
            echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/$term"
            ;;
        # Array methods
        map|filter|reduce|forEach|find|findIndex|some|every|includes|indexOf|slice|splice|concat|join|push|pop|shift|unshift|sort|reverse|flat|flatMap)
            echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/$term"
            ;;
        # String methods
        split|replace|match|search|substring|substr|toLowerCase|toUpperCase|trim|padStart|padEnd|startsWith|endsWith|charAt|charCodeAt)
            echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/$term"
            ;;
        # Promise methods
        then|resolve|reject|all|race|allSettled|any)
            echo "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/$term"
            ;;
        # Common Web APIs
        fetch|console|document|window|localStorage|sessionStorage|setTimeout|setInterval|addEventListener|querySelector|querySelectorAll)
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
        interface|type|enum|namespace|declare|readonly|abstract|implements|extends|keyof|typeof|infer|as|is|asserts|satisfies|override)
            echo "https://www.typescriptlang.org/docs/handbook/2/everyday-types.html"
            ;;
        Partial|Required|Readonly|Record|Pick|Omit|Exclude|Extract|NonNullable|ReturnType|Parameters|InstanceType|Awaited)
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
        if|else|for|while|do|switch|case|break|continue|return|goto|sizeof|typedef|struct|union|enum|const|static|extern|register|volatile|inline|restrict|_Bool|_Complex|_Imaginary|_Alignas|_Alignof|_Atomic|_Generic|_Noreturn|_Static_assert|_Thread_local)
            echo "https://en.cppreference.com/w/c/keyword/$term"
            ;;
        # Standard library headers
        stdio|stdlib|string|math|time|ctype|stdint|stdbool|stddef|limits|float|errno|assert|signal|setjmp|stdarg|locale)
            echo "https://en.cppreference.com/w/c/header/${term}.h"
            ;;
        # Common functions
        printf|fprintf|sprintf|snprintf|scanf|fscanf|sscanf|fopen|fclose|fread|fwrite|fgets|fputs|fseek|ftell|rewind|fflush)
            echo "https://en.cppreference.com/w/c/io"
            ;;
        malloc|calloc|realloc|free|memcpy|memmove|memset|memcmp)
            echo "https://en.cppreference.com/w/c/memory"
            ;;
        strlen|strcpy|strncpy|strcat|strncat|strcmp|strncmp|strchr|strrchr|strstr|strtok)
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
        class|public|private|protected|virtual|override|final|explicit|mutable|constexpr|consteval|constinit|concept|requires|co_await|co_yield|co_return|nullptr|noexcept|decltype|auto|template|typename|namespace|using|new|delete|throw|try|catch|static_cast|dynamic_cast|const_cast|reinterpret_cast)
            echo "https://en.cppreference.com/w/cpp/keyword/$term"
            ;;
        # STL containers
        vector|list|deque|array|forward_list|set|map|unordered_set|unordered_map|multiset|multimap|stack|queue|priority_queue)
            echo "https://en.cppreference.com/w/cpp/container/$term"
            ;;
        # STL algorithms
        sort|find|copy|move|transform|accumulate|count|remove|unique|reverse|rotate|shuffle|partition|merge|binary_search|lower_bound|upper_bound)
            echo "https://en.cppreference.com/w/cpp/algorithm/$term"
            ;;
        # Smart pointers
        unique_ptr|shared_ptr|weak_ptr|make_unique|make_shared)
            echo "https://en.cppreference.com/w/cpp/memory/$term"
            ;;
        # Common classes
        string|string_view|optional|variant|any|tuple|pair|function|bind|thread|mutex|future|promise|chrono)
            echo "https://en.cppreference.com/w/cpp/utility"
            ;;
        *)
            # Try C docs as fallback
            c_doc_url "$term"
            ;;
    esac
}

# Rust documentation
rust_doc_url() {
    local term="$1"
    
    case "$term" in
        # Keywords
        fn|let|mut|const|static|if|else|match|loop|while|for|in|break|continue|return|struct|enum|impl|trait|type|where|pub|mod|use|crate|self|super|async|await|move|ref|dyn|unsafe|extern)
            echo "https://doc.rust-lang.org/std/keyword.$term.html"
            ;;
        # Common types
        Option|Result|Vec|String|Box|Rc|Arc|Cell|RefCell|Mutex|RwLock|HashMap|HashSet|BTreeMap|BTreeSet)
            echo "https://doc.rust-lang.org/std/$term"
            ;;
        # Traits
        Clone|Copy|Debug|Default|Eq|PartialEq|Ord|PartialOrd|Hash|Display|From|Into|AsRef|AsMut|Deref|DerefMut|Iterator|IntoIterator|Send|Sync)
            echo "https://doc.rust-lang.org/std/$term"
            ;;
        # Macros
        println|print|format|vec|panic|assert|assert_eq|assert_ne|debug_assert|todo|unimplemented|unreachable)
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
        func|var|const|type|struct|interface|map|chan|go|select|defer|if|else|for|range|switch|case|default|break|continue|return|goto|fallthrough|package|import)
            echo "https://go.dev/ref/spec"
            ;;
        # Built-in functions
        make|new|len|cap|append|copy|delete|close|panic|recover|print|println|complex|real|imag)
            echo "https://pkg.go.dev/builtin#$term"
            ;;
        # Common packages
        fmt|os|io|net|http|json|time|strings|strconv|errors|context|sync|testing|reflect|regexp|sort|math|crypto|encoding|bufio|bytes|path|filepath)
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
        if|else|elsif|unless|case|when|while|until|for|do|end|begin|rescue|ensure|raise|return|break|next|redo|retry|yield|def|class|module|self|super|nil|true|false|and|or|not|in|then|alias|defined|__FILE__|__LINE__|__ENCODING__)
            echo "https://ruby-doc.org/docs/keywords/1.9/"
            ;;
        # Core classes
        String|Array|Hash|Integer|Float|Symbol|Range|Regexp|Time|Date|File|Dir|IO|Proc|Lambda|Method|Thread|Mutex|Fiber)
            echo "https://ruby-doc.org/core/classes/$term.html"
            ;;
        # Enumerable methods
        each|map|select|reject|find|reduce|inject|collect|detect|sort|sort_by|group_by|partition|any|all|none|one|count|first|last|take|drop)
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
        if|else|for|while|do|switch|case|break|continue|return|throw|try|catch|finally|class|interface|enum|extends|implements|new|this|super|static|final|abstract|public|private|protected|void|null|true|false|instanceof|synchronized|volatile|transient|native|strictfp|assert|default|package|import)
            echo "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/"
            ;;
        # Common classes
        String|Integer|Long|Double|Float|Boolean|Character|Object|Class|System|Math|Arrays|Collections|List|ArrayList|LinkedList|Map|HashMap|TreeMap|Set|HashSet|TreeSet|Queue|Stack|Optional|Stream)
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
        if|then|else|elif|fi|for|while|until|do|done|case|esac|in|function|select|time|coproc)
            echo "https://www.gnu.org/software/bash/manual/bash.html#Conditional-Constructs"
            ;;
        echo|printf|read|declare|local|export|unset|set|shopt|alias|source|eval|exec|exit|return|break|continue|shift|trap|wait|kill|jobs|bg|fg|disown|suspend|logout|cd|pwd|pushd|popd|dirs|type|which|command|builtin|enable|help|hash|bind|complete|compgen|compopt)
            echo "https://www.gnu.org/software/bash/manual/bash.html#Shell-Builtin-Commands"
            ;;
        # Common external commands
        grep|sed|awk|find|xargs|sort|uniq|cut|tr|head|tail|wc|cat|tee|diff|patch|tar|gzip|zip|curl|wget|ssh|scp|rsync|git|make|chmod|chown|chgrp|ln|cp|mv|rm|mkdir|rmdir|touch|ls|stat|file|df|du|free|top|ps|kill|pkill|pgrep|nohup|screen|tmux)
            echo "https://man7.org/linux/man-pages/man1/$term.1.html"
            ;;
        *)
            echo "https://www.gnu.org/software/bash/manual/bash.html"
            ;;
    esac
}

#==============================================================================
# Get documentation URL for a term based on detected language
#==============================================================================
get_doc_url() {
    local term="$1"
    local lang="$2"
    local import_line="$3"  # Optional: full import for context
    
    # Try offline docs first
    local offline_result
    offline_result=$(lookup_offline "$term" "$lang" "$import_line")
    if [ -n "$offline_result" ]; then
        echo "$offline_result"
        return 0
    fi
    
    # For TypeScript, also try JavaScript offline docs (most TS keywords are JS)
    if [[ "$lang" == "typescript" || "$lang" == "ts" || "$lang" == "tsx" ]]; then
        offline_result=$(lookup_offline "$term" "js" "$import_line")
        if [ -n "$offline_result" ]; then
            echo "$offline_result"
            return 0
        fi
    fi
    
    # Fall back to online URLs
    case "$lang" in
        python|py)
            python_doc_url "$term"
            ;;
        javascript|js|jsx)
            js_doc_url "$term"
            ;;
        typescript|ts|tsx)
            # For TypeScript, try JS doc first (since most keywords are shared)
            # Only use TS-specific docs for TS-only features
            case "$term" in
                interface|type|enum|namespace|declare|readonly|abstract|implements|keyof|infer|as|is|asserts|satisfies|override|Partial|Required|Readonly|Record|Pick|Omit|Exclude|Extract|NonNullable|ReturnType|Parameters|InstanceType|Awaited)
                    ts_doc_url "$term"
                    ;;
                *)
                    js_doc_url "$term"
                    ;;
            esac
            ;;
        c)
            c_doc_url "$term"
            ;;
        cpp|c++|cc|cxx)
            cpp_doc_url "$term"
            ;;
        rust|rs)
            rust_doc_url "$term"
            ;;
        go)
            go_doc_url "$term"
            ;;
        ruby|rb)
            ruby_doc_url "$term"
            ;;
        java)
            java_doc_url "$term"
            ;;
        shell|bash|sh)
            shell_doc_url "$term"
            ;;
        *)
            echo "https://devdocs.io/#q=$term"
            ;;
    esac
}

#==============================================================================
# Detect primary language from results
#==============================================================================
detect_language() {
    if [ -f "$RESULTS_DIR/tokei_stats.txt" ]; then
        # Parse tokei output to find most used language
        grep -E "^\s+(Python|JavaScript|TypeScript|C\+\+|C |Rust|Go|Ruby|Java|Shell)" "$RESULTS_DIR/tokei_stats.txt" 2>/dev/null \
            | head -1 \
            | awk '{print tolower($1)}' \
            | sed 's/c++/cpp/'
    else
        echo "unknown"
    fi
}

#==============================================================================
# Main Processing
#==============================================================================

# Check if results directory exists
if [ ! -d "$RESULTS_DIR" ]; then
    echo -e "${RED}Error: Results directory not found: $RESULTS_DIR${NC}"
    echo "Run analyze_repo.sh first to generate analysis results."
    exit 1
fi

# Detect or use specified language
if [ "$LANGUAGES" = "auto" ]; then
    PRIMARY_LANG=$(detect_language)
    echo -e "${BLUE}Detected primary language: ${GREEN}$PRIMARY_LANG${NC}"
else
    PRIMARY_LANG=$(echo "$LANGUAGES" | cut -d',' -f1)
    echo -e "${BLUE}Using specified language: ${GREEN}$PRIMARY_LANG${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Generating Study Materials${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
# Patch for generate_study_materials.sh - use per-language files

#==============================================================================
# Generate Documentation Links (Markdown)
#==============================================================================
echo -e "${YELLOW}Generating documentation links...${NC}"

cat > "$DOCS_FILE" << 'EOF'
# Documentation Links for Code Review

This document contains links to official documentation for the most commonly used
functions, keywords, and patterns found in the analyzed codebase.

**Note:** Items are grouped by language for accurate documentation links.

---

EOF

# Check for per-language files
PER_LANG_DIR="$RESULTS_DIR/per_language"

if [ -d "$PER_LANG_DIR" ]; then
    echo -e "${GREEN}Using per-language analysis files${NC}"
    
    # Map internal lang names to doc function names
    lang_to_doc() {
        case "$1" in
            c_cpp) echo "cpp" ;;
            javascript) echo "js" ;;
            typescript) echo "ts" ;;
            shell) echo "bash" ;;
            *) echo "$1" ;;
        esac
    }
    
    # Process keywords by language
    echo "## Language Keywords" >> "$DOCS_FILE"
    echo "" >> "$DOCS_FILE"
    
    for keyword_file in "$PER_LANG_DIR"/keywords_*.txt; do
        [ ! -f "$keyword_file" ] && continue
        [ ! -s "$keyword_file" ] && continue
        
        # Extract language name from filename
        lang=$(basename "$keyword_file" | sed 's/keywords_//; s/\.txt//')
        doc_lang=$(lang_to_doc "$lang")
        
        # Format language name for display
        case "$lang" in
            c_cpp) display_lang="C/C++" ;;
            javascript) display_lang="JavaScript" ;;
            typescript) display_lang="TypeScript" ;;
            python) display_lang="Python" ;;
            rust) display_lang="Rust" ;;
            go) display_lang="Go" ;;
            ruby) display_lang="Ruby" ;;
            java) display_lang="Java" ;;
            shell) display_lang="Shell/Bash" ;;
            *) display_lang="$lang" ;;
        esac
        
        echo "### $display_lang Keywords" >> "$DOCS_FILE"
        echo "" >> "$DOCS_FILE"
        echo "| Keyword | Count | Documentation |" >> "$DOCS_FILE"
        echo "|---------|-------|---------------|" >> "$DOCS_FILE"
        
        head -$TOP_N "$keyword_file" | while read -r count term; do
            [ -z "$term" ] && continue
            [[ "$term" =~ ^[#] ]] && continue  # Skip comment lines
            url=$(get_doc_url "$term" "$doc_lang")
            echo "| \`$term\` | $count | [docs]($url) |" >> "$DOCS_FILE"
        done
        echo "" >> "$DOCS_FILE"
    done
    
    # Process functions by language
    echo "## Function/Method Calls" >> "$DOCS_FILE"
    echo "" >> "$DOCS_FILE"
    
    for func_file in "$PER_LANG_DIR"/functions_*.txt; do
        [ ! -f "$func_file" ] && continue
        [ ! -s "$func_file" ] && continue
        
        lang=$(basename "$func_file" | sed 's/functions_//; s/\.txt//')
        doc_lang=$(lang_to_doc "$lang")
        
        case "$lang" in
            c_cpp) display_lang="C/C++" ;;
            javascript) display_lang="JavaScript" ;;
            typescript) display_lang="TypeScript" ;;
            python) display_lang="Python" ;;
            rust) display_lang="Rust" ;;
            go) display_lang="Go" ;;
            ruby) display_lang="Ruby" ;;
            java) display_lang="Java" ;;
            shell) display_lang="Shell/Bash" ;;
            *) display_lang="$lang" ;;
        esac
        
        echo "### $display_lang Functions" >> "$DOCS_FILE"
        echo "" >> "$DOCS_FILE"
        echo "| Function | Count | Documentation |" >> "$DOCS_FILE"
        echo "|----------|-------|---------------|" >> "$DOCS_FILE"
        
        head -$TOP_N "$func_file" | while read -r count term; do
            [ -z "$term" ] && continue
            [[ "$term" =~ ^(if|for|while|switch|catch|elif)$ ]] && continue
            url=$(get_doc_url "$term" "$doc_lang")
            echo "| \`$term()\` | $count | [docs]($url) |" >> "$DOCS_FILE"
        done
        echo "" >> "$DOCS_FILE"
    done
    
    # Process imports by language
    echo "## Imports/Includes" >> "$DOCS_FILE"
    echo "" >> "$DOCS_FILE"
    
    for import_file in "$PER_LANG_DIR"/imports_*.txt; do
        [ ! -f "$import_file" ] && continue
        [ ! -s "$import_file" ] && continue
        
        lang=$(basename "$import_file" | sed 's/imports_//; s/\.txt//')
        doc_lang=$(lang_to_doc "$lang")
        
        case "$lang" in
            c_cpp) display_lang="C/C++ (#include)" ;;
            javascript) display_lang="JavaScript (import/require)" ;;
            typescript) display_lang="TypeScript (import)" ;;
            python) display_lang="Python (import/from)" ;;
            rust) display_lang="Rust (use)" ;;
            go) display_lang="Go (import)" ;;
            ruby) display_lang="Ruby (require)" ;;
            java) display_lang="Java (import)" ;;
            shell) display_lang="Shell (source)" ;;
            *) display_lang="$lang" ;;
        esac
        
        echo "### $display_lang" >> "$DOCS_FILE"
        echo "" >> "$DOCS_FILE"
        echo "| Import | Count | Documentation |" >> "$DOCS_FILE"
        echo "|--------|-------|---------------|" >> "$DOCS_FILE"
        
        head -20 "$import_file" | while read -r count import; do
            [ -z "$import" ] && continue
            # For offline lookup, pass the full import line for better context
            url=$(get_doc_url "" "$doc_lang" "$import")
            if [ -z "$url" ] || [[ "$url" == *"search.html"* ]]; then
                # Fallback: extract module and try again
                module=$(echo "$import" | sed -E 's/.*[<"]([^">]+)[">].*/\1/' | sed 's|.*/||' | sed 's/\..*$//')
                url=$(get_doc_url "$module" "$doc_lang")
            fi
            import_escaped=$(echo "$import" | sed 's/|/\\|/g')
            echo "| \`$import_escaped\` | $count | [docs]($url) |" >> "$DOCS_FILE"
        done
        echo "" >> "$DOCS_FILE"
    done
    
else
    # Fallback to combined files (old behavior)
    echo -e "${YELLOW}No per-language files found, using combined analysis${NC}"
    
    if [ -f "$RESULTS_DIR/grep_keywords.txt" ]; then
        echo "## Language Keywords" >> "$DOCS_FILE"
        echo "" >> "$DOCS_FILE"
        echo "| Keyword | Count | Documentation |" >> "$DOCS_FILE"
        echo "|---------|-------|---------------|" >> "$DOCS_FILE"
        
        head -$TOP_N "$RESULTS_DIR/grep_keywords.txt" | while read -r count term; do
            [ -z "$term" ] && continue
            url=$(get_doc_url "$term" "$PRIMARY_LANG")
            echo "| \`$term\` | $count | [docs]($url) |" >> "$DOCS_FILE"
        done
        echo "" >> "$DOCS_FILE"
    fi
    
    if [ -f "$RESULTS_DIR/grep_function_calls.txt" ]; then
        echo "## Function/Method Calls" >> "$DOCS_FILE"
        echo "" >> "$DOCS_FILE"
        echo "| Function | Count | Documentation |" >> "$DOCS_FILE"
        echo "|----------|-------|---------------|" >> "$DOCS_FILE"
        
        head -$TOP_N "$RESULTS_DIR/grep_function_calls.txt" | while read -r count term; do
            [ -z "$term" ] && continue
            [[ "$term" =~ ^(if|for|while|switch|catch)$ ]] && continue
            url=$(get_doc_url "$term" "$PRIMARY_LANG")
            echo "| \`$term()\` | $count | [docs]($url) |" >> "$DOCS_FILE"
        done
        echo "" >> "$DOCS_FILE"
    fi
    
    if [ -f "$RESULTS_DIR/grep_imports.txt" ]; then
        echo "## Imports/Includes" >> "$DOCS_FILE"
        echo "" >> "$DOCS_FILE"
        echo "| Import | Count | Documentation |" >> "$DOCS_FILE"
        echo "|--------|-------|---------------|" >> "$DOCS_FILE"
        
        head -20 "$RESULTS_DIR/grep_imports.txt" | while read -r count import; do
            [ -z "$import" ] && continue
            module=$(echo "$import" | sed -E 's/.*[<"]([^">]+)[">].*/\1/' | sed 's|.*/||' | sed 's/\..*$//')
            url=$(get_doc_url "$module" "$PRIMARY_LANG")
            import_escaped=$(echo "$import" | sed 's/|/\\|/g')
            echo "| \`$import_escaped\` | $count | [docs]($url) |" >> "$DOCS_FILE"
        done
        echo "" >> "$DOCS_FILE"
    fi
fi

echo "" >> "$DOCS_FILE"
echo "---" >> "$DOCS_FILE"
echo "*Generated by analyze_repo.sh + generate_study_materials.sh*" >> "$DOCS_FILE"

echo -e "${GREEN}Created: $DOCS_FILE${NC}"
#==============================================================================
# Generate Anki Cards (Tab-separated for import)
#==============================================================================
echo -e "${YELLOW}Generating Anki cards...${NC}"

cat > "$ANKI_FILE" << 'EOF'
# Anki Import File
# Format: Front<TAB>Back<TAB>Tags
# Import with: File -> Import, select "Fields separated by: Tab"
#
# Card Types:
# 1. "What does X do?" - For functions/methods
# 2. "When to use X?" - For keywords/patterns
# 3. "What is the syntax for X?" - For language constructs
#
EOF

# Generate cards for top keywords
if [ -f "$RESULTS_DIR/grep_keywords.txt" ]; then
    echo "# Keywords" >> "$ANKI_FILE"
    head -$TOP_N "$RESULTS_DIR/grep_keywords.txt" | while read -r count term; do
        [ -z "$term" ] && continue
        url=$(get_doc_url "$term" "$PRIMARY_LANG")
        
        # Create different card types based on term type
        case "$term" in
            if|else|elif|elseif|switch|case|match)
                echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tConditional control flow - executes code based on boolean conditions. See: $url\t${PRIMARY_LANG}::keywords::control-flow" >> "$ANKI_FILE"
                ;;
            for|while|loop|do|until)
                echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tLoop construct - repeats code execution. See: $url\t${PRIMARY_LANG}::keywords::loops" >> "$ANKI_FILE"
                ;;
            try|except|catch|finally|raise|throw)
                echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tException handling - manages errors and exceptional conditions. See: $url\t${PRIMARY_LANG}::keywords::exceptions" >> "$ANKI_FILE"
                ;;
            class|struct|interface|trait|impl)
                echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tType definition - defines custom data structures. See: $url\t${PRIMARY_LANG}::keywords::types" >> "$ANKI_FILE"
                ;;
            def|fn|func|function)
                echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tFunction definition - declares a reusable block of code. See: $url\t${PRIMARY_LANG}::keywords::functions" >> "$ANKI_FILE"
                ;;
            import|from|use|require|include)
                echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tModule import - brings external code into current scope. See: $url\t${PRIMARY_LANG}::keywords::modules" >> "$ANKI_FILE"
                ;;
            async|await|yield)
                echo -e "What is the purpose of \`$term\` in $PRIMARY_LANG?\tAsynchronous programming - handles concurrent operations. See: $url\t${PRIMARY_LANG}::keywords::async" >> "$ANKI_FILE"
                ;;
            *)
                echo -e "What does the keyword \`$term\` do in $PRIMARY_LANG?\t[FILL: Look up at $url]\t${PRIMARY_LANG}::keywords" >> "$ANKI_FILE"
                ;;
        esac
    done
fi

# Generate cards for top functions
if [ -f "$RESULTS_DIR/grep_function_calls.txt" ]; then
    echo "" >> "$ANKI_FILE"
    echo "# Functions" >> "$ANKI_FILE"
    head -$TOP_N "$RESULTS_DIR/grep_function_calls.txt" | while read -r count term; do
        [ -z "$term" ] && continue
        [[ "$term" =~ ^(if|for|while|switch|catch)$ ]] && continue
        url=$(get_doc_url "$term" "$PRIMARY_LANG")
        
        echo -e "What does \`$term()\` do in $PRIMARY_LANG? (Used $count times)\t[FILL: Look up at $url]\t${PRIMARY_LANG}::functions" >> "$ANKI_FILE"
    done
fi

echo -e "${GREEN}Created: $ANKI_FILE${NC}"

#==============================================================================
# Generate LLM Prompt for Anki Card Generation
#==============================================================================
echo -e "${YELLOW}Generating LLM prompt...${NC}"

# Helper function to get doc link for a term
get_llm_doc_link() {
    local term="$1"
    local lang="$2"
    local is_import="$3"  # "true" if it's an import line
    
    # Check if it's an internal/project-specific item
    if [[ "$term" =~ ^@/ ]] || [[ "$term" =~ ^\./ ]] || [[ "$term" =~ ^app\. ]] || [[ "$term" =~ ^src/ ]] || [[ "$term" =~ from\ \'@/ ]] || [[ "$term" =~ from\ \'\./ ]]; then
        echo "[INTERNAL - SKIP]"
        return
    fi
    
    # Try offline lookup
    local offline_result
    if [ "$is_import" = "true" ]; then
        offline_result=$("$LOOKUP_SCRIPT" --import "$term" "$lang" 2>/dev/null | grep "^/" | head -1)
    else
        offline_result=$("$LOOKUP_SCRIPT" "$term" "$lang" 2>/dev/null | grep "^File:" | head -1 | sed 's/^File: //')
    fi
    
    if [ -n "$offline_result" ]; then
        echo "$offline_result"
    else
        echo "[NO OFFLINE DOC]"
    fi
}

# Generate keywords with doc links
generate_keywords_with_docs() {
    local keywords_file="$RESULTS_DIR/grep_keywords.txt"
    [ ! -f "$keywords_file" ] && echo "No keywords found" && return
    
    head -$TOP_N "$keywords_file" | grep -v '^#' | while read -r line; do
        local count=$(echo "$line" | awk '{print $1}')
        local keyword=$(echo "$line" | awk '{print $2}')
        [ -z "$keyword" ] && continue
        local doc_link=$(get_llm_doc_link "$keyword" "$PRIMARY_LANG" "false")
        echo "$count $keyword → $doc_link"
    done
}

# Generate functions with doc links
generate_functions_with_docs() {
    local functions_file="$RESULTS_DIR/grep_function_calls.txt"
    [ ! -f "$functions_file" ] && echo "No functions found" && return
    
    head -$TOP_N "$functions_file" | grep -v '^#' | while read -r line; do
        local count=$(echo "$line" | awk '{print $1}')
        local func=$(echo "$line" | awk '{print $2}')
        
        # Skip single-letter functions (minified code) or empty
        if [ -z "$func" ] || [ ${#func} -le 1 ]; then
            continue
        fi
        
        local doc_link=$(get_llm_doc_link "$func" "$PRIMARY_LANG" "false")
        echo "$count $func() → $doc_link"
    done
}

# Generate imports with doc links
generate_imports_with_docs() {
    local imports_file="$RESULTS_DIR/grep_imports.txt"
    [ ! -f "$imports_file" ] && echo "No imports found" && return
    
    head -20 "$imports_file" | grep -v '^#' | while read -r line; do
        local count=$(echo "$line" | awk '{print $1}')
        local import_stmt=$(echo "$line" | cut -d' ' -f2-)
        [ -z "$import_stmt" ] && continue
        
        # Check if internal import
        if [[ "$import_stmt" =~ @/ ]] || [[ "$import_stmt" =~ \'\./ ]] || [[ "$import_stmt" =~ from\ app\. ]] || [[ "$import_stmt" =~ from\ src\. ]]; then
            echo "$count $import_stmt → [INTERNAL - SKIP]"
        else
            local doc_link=$(get_llm_doc_link "$import_stmt" "$PRIMARY_LANG" "true")
            echo "$count $import_stmt → $doc_link"
        fi
    done
}

cat > "$LLM_PROMPT_FILE" << 'PROMPT_HEADER'
# LLM Prompt: Generate Anki Flashcards

You are creating Anki flashcards from code analysis.

## CRITICAL INSTRUCTIONS

1. **READ DOCS VIA TERMINAL** - Use the `cat` command to read each .md file:
   ```
   cat /home/kuhy/.local/share/offline-docs/mdn-content/files/en-us/web/javascript/reference/statements/const/index.md
   ```
2. **DO NOT USE YOUR OWN KNOWLEDGE** - Base flashcards ONLY on the content you read from the files
3. **IF YOU CANNOT READ A FILE** - Report: "ERROR: Cannot read [path]" and skip that item
4. **NEVER FALL BACK TO GENERAL KNOWLEDGE** - If you can't read the file, skip it entirely
5. **READ ONE FILE AT A TIME** - Run cat for each topic before creating its flashcards

PROMPT_HEADER

cat >> "$LLM_PROMPT_FILE" << EOF
## Context
- Primary Language: **$PRIMARY_LANG**

## Top Keywords (by frequency)
Items marked \`[INTERNAL - SKIP]\` are project-specific - skip them.
Items marked \`[NO OFFLINE DOC]\` have no offline documentation - use online docs or skip.
Other items have offline doc paths you can reference.

\`\`\`
$(generate_keywords_with_docs)
\`\`\`

## Top Functions/Methods (by frequency)
\`\`\`
$(generate_functions_with_docs)
\`\`\`

## Top Imports/Includes
\`\`\`
$(generate_imports_with_docs)
\`\`\`
EOF

cat >> "$LLM_PROMPT_FILE" << 'PROMPT_FOOTER'

## Guidelines

**CRITICAL - Keep answers EXTREMELY short:**
- Most answers should be **1-2 words** or **1 sentence**
- It's common and expected for an answer to be just: "Returns an array" or "Immutable"
- 2 sentences = longer answer, 3 sentences = absolute maximum (rare)
- Each flashcard tests ONE atomic piece of knowledge

**NO DUPLICATES:**
- Before creating a card, check if you already created a similar question
- Each unique fact should appear in EXACTLY ONE card
- Do NOT create multiple cards asking the same thing with slightly different wording

**What to include:**
- Concept cards: "What is X?" / "What does X do?"
- Syntax cards: "How do you write X?" (brief code snippet)
- Comparison cards: "X vs Y - what's the difference?"

**What to SKIP (do NOT create cards for):**
- MDN frontmatter fields: title, slug, page-type, browser-compat, spec-urls
- YAML metadata between `---` markers at the start of files
- Any line that looks like metadata (key: value at start of doc)
- Empty answers - if you can't find content for the back, skip the card entirely

**FINAL CARD FOR EACH TOPIC (EXCEPTION TO SHORT ANSWER RULE):**
- Add EXACTLY ONE full documentation card per topic (no duplicates!)
- Question: `[Topic] - Full MDN Documentation`
- Answer: Copy the .md file content STARTING AFTER the `---` frontmatter block
- Skip the YAML frontmatter (everything between the first two `---` lines)
- Do NOT create this card twice for the same topic

**Skipped items - please review:**
- Items marked `[INTERNAL - SKIP]` are project-specific utilities - I skipped them
- Items marked `[NO OFFLINE DOC]` are third-party libraries without bundled docs
- If you want flashcards for skipped items, tell me which ones to include

## OUTPUT: CREATE AN ANKI FILE

**CREATE A FILE DIRECTLY** - Do not just output text. Use your file creation tool to create:

**File path:** `~/.local/share/study-materials/anki_generated.txt`

**Format:** Tab-separated values (TSV) with Anki metadata headers:

```
#separator:tab
#deck:CodeStudy::JavaScript
#notetype:CodeCard
#columns:Front	Back	Tags
What does <code>const</code> declare?Block-scoped variables with immutable bindings.javascript declarations
```

**Required headers at top of file:**
- `#separator:tab` - Specifies tab as delimiter
- `#deck:CodeStudy::[Language]` - Creates deck "CodeStudy" with sub-deck for language (e.g., CodeStudy::JavaScript)
- `#notetype:CodeCard` - Uses custom note type "CodeCard" (Anki will create if doesn't exist)
- `#columns:Front	Back	Tags` - Column headers (tab-separated)

**Rules:**
- Use ACTUAL `<code>` tags (not escaped &lt;code&gt;)
- Use `<br>` for line breaks within fields
- Use `<pre>` for code blocks  
- Tags are space-separated
- Escape any literal tabs within content as spaces

**Example file content:**
```
#separator:tab
#deck:CodeStudy::JavaScript
#notetype:CodeCard
#columns:Front	Back	Tags
What does <code>const</code> declare?Block-scoped variables with immutable bindings.javascript declarations
Can <code>const</code> be reassigned?No, throws TypeError.javascript declarations
const - Full Documentation<pre>[ENTIRE CONTENT OF const/index.md FILE]</pre>javascript declarations full-doc
```

**After creating the file**, tell the user:
- File created at: ~/.local/share/study-materials/anki_generated.txt
- Import in Anki: File → Import → select the file
- Deck: CodeStudy::[Language], Note type: CodeCard
---

**Important:** 
- Process only 5-10 items at a time to maintain quality
- Focus on items with offline documentation paths
- Output ONLY the TSV lines, no extra formatting or markdown
PROMPT_FOOTER

echo -e "${GREEN}Created: $LLM_PROMPT_FILE${NC}"


#==============================================================================
# Summary
#==============================================================================
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Study Materials Generated!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Files created:"
echo "  📚 Documentation Links: $DOCS_FILE"
echo "  🎴 Anki Cards:          $ANKI_FILE"
echo "  🤖 LLM Prompt:          $LLM_PROMPT_FILE"
echo ""
echo "Next steps:"
echo "  1. Review documentation_links.md for learning resources"
echo "  2. Import anki_cards.txt into Anki (File -> Import)"
echo "  3. Use llm_anki_prompt.md with ChatGPT/Claude to generate more cards"
echo ""
echo "Anki import settings:"
echo "  - Field separator: Tab"
echo "  - Allow HTML: Yes"
echo "  - Tags are in last field: Yes"
