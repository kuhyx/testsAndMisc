#!/bin/bash
# Analyze a git repository for most-used keywords, functions, etc.
# Usage: ./analyze_repo.sh [repo_url_or_local_path] [output_dir] [--no-ignore]
#
# Examples:
#   ./analyze_repo.sh https://github.com/torvalds/linux    # Clone from URL
#   ./analyze_repo.sh /path/to/local/repo                  # Use local directory
#   ./analyze_repo.sh .                                    # Analyze current directory
#   ./analyze_repo.sh . /tmp/out --no-ignore               # Include node_modules, etc.

set -e

# Parse arguments
INPUT=""
WORK_DIR=""
RESPECT_GITIGNORE=true

for arg in "$@"; do
	case "$arg" in
	--no-ignore)
		RESPECT_GITIGNORE=false
		;;
	*)
		if [ -z "$INPUT" ]; then
			INPUT="$arg"
		elif [ -z "$WORK_DIR" ]; then
			WORK_DIR="$arg"
		fi
		;;
	esac
done

INPUT="${INPUT:-https://github.com/torvalds/linux}"
WORK_DIR="${WORK_DIR:-/tmp/repo_analysis}"
TOP_N=50 # Number of top results to show

# Directories to exclude (unless --no-ignore is used)
EXCLUDE_DIRS="node_modules|\.git|vendor|\.venv|venv|__pycache__|\.cache|build|dist|\.next|\.nuxt|target|\.tox|\.eggs"

# Detect if input is a URL or local path
is_url() {
	[[ $1 =~ ^https?:// ]] || [[ $1 =~ ^git@ ]] || [[ $1 =~ ^ssh:// ]]
}

IS_LOCAL=false
if is_url "$INPUT"; then
	REPO_URL="$INPUT"
	REPO_NAME=$(basename "$REPO_URL" .git)
	REPO_DIR="$WORK_DIR/$REPO_NAME"
else
	# Local path - resolve to absolute path
	IS_LOCAL=true
	if [ -d "$INPUT" ]; then
		REPO_DIR=$(cd "$INPUT" && pwd)
		REPO_NAME=$(basename "$REPO_DIR")
	else
		echo "Error: '$INPUT' is not a valid directory or URL"
		exit 1
	fi
fi

RESULTS_DIR="$WORK_DIR/results_${REPO_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
	echo ""
	echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
	echo -e "${GREEN}  $1${NC}"
	echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
	echo ""
}

print_subheader() {
	echo ""
	echo -e "${YELLOW}--- $1 ---${NC}"
	echo ""
}

# Check if we're in a git repository
is_git_repo() {
	git rev-parse --is-inside-work-tree &>/dev/null
}

# Helper function to find files while respecting exclusions
# Usage: find_files "*.c" or find_files "*.py" "*.pyx"
find_files() {
	local patterns=("$@")

	if [ "$RESPECT_GITIGNORE" = true ]; then
		if is_git_repo; then
			# Use git ls-files which respects .gitignore automatically
			# This includes tracked files and untracked files not in .gitignore
			local git_patterns=()
			for pat in "${patterns[@]}"; do
				git_patterns+=("$pat")
			done
			# Get tracked files + untracked (but not ignored) files
			{
				git ls-files -- "${git_patterns[@]}" 2>/dev/null
				git ls-files --others --exclude-standard -- "${git_patterns[@]}" 2>/dev/null
			} | sort -u
		else
			# Not a git repo - fall back to manual exclusion
			local find_args=()
			for i in "${!patterns[@]}"; do
				if [ $i -eq 0 ]; then
					find_args+=(-name "${patterns[$i]}")
				else
					find_args+=(-o -name "${patterns[$i]}")
				fi
			done
			find . -type f \( "${find_args[@]}" \) 2>/dev/null | grep -Ev "/($EXCLUDE_DIRS)/"
		fi
	else
		# No filtering - find all files
		local find_args=()
		for i in "${!patterns[@]}"; do
			if [ $i -eq 0 ]; then
				find_args+=(-name "${patterns[$i]}")
			else
				find_args+=(-o -name "${patterns[$i]}")
			fi
		done
		find . -type f \( "${find_args[@]}" \) 2>/dev/null
	fi
}

# Count files matching pattern (respecting exclusions)
count_files() {
	find_files "$@" | wc -l
}

#==============================================================================
# STEP 0: Install Missing Tools
#==============================================================================
install_missing_tools() {
	local MISSING_TOOLS=()
	local MISSING_AUR=()

	# Check for required tools
	command -v git &>/dev/null || MISSING_TOOLS+=("git")
	command -v ctags &>/dev/null || MISSING_TOOLS+=("ctags")
	command -v cscope &>/dev/null || MISSING_TOOLS+=("cscope")
	command -v clang &>/dev/null || MISSING_TOOLS+=("clang")
	command -v ugrep &>/dev/null || MISSING_TOOLS+=("ugrep")

	# Check for AUR tools
	command -v tokei &>/dev/null || MISSING_AUR+=("tokei")
	command -v scc &>/dev/null || MISSING_AUR+=("scc")

	# Check for Rust 'counts' tool (install via cargo if missing)
	if ! command -v counts &>/dev/null; then
		if command -v cargo &>/dev/null; then
			echo "Installing 'counts' via cargo (fast word counter)..."
			cargo install counts 2>/dev/null || echo "Warning: counts install failed, will use Python fallback"
		fi
	fi

	# If nothing is missing, return
	if [ ${#MISSING_TOOLS[@]} -eq 0 ] && [ ${#MISSING_AUR[@]} -eq 0 ]; then
		echo -e "${GREEN}All required tools are installed.${NC}"
		return 0
	fi

	echo -e "${YELLOW}Missing tools detected. Installing...${NC}"

	# Detect package manager
	if command -v pacman &>/dev/null; then
		# Arch Linux
		if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
			echo "Installing from official repos: ${MISSING_TOOLS[*]}"
			sudo pacman -S --needed --noconfirm "${MISSING_TOOLS[@]}"
		fi

		if [ ${#MISSING_AUR[@]} -gt 0 ]; then
			# Find or install AUR helper
			if command -v yay &>/dev/null; then
				AUR_HELPER="yay"
			elif command -v paru &>/dev/null; then
				AUR_HELPER="paru"
			else
				echo "No AUR helper found. Installing yay..."
				sudo pacman -S --needed --noconfirm base-devel git
				TEMP_DIR=$(mktemp -d)
				git clone https://aur.archlinux.org/yay.git "$TEMP_DIR/yay"
				(cd "$TEMP_DIR/yay" && makepkg -si --noconfirm)
				rm -rf "$TEMP_DIR"
				AUR_HELPER="yay"
			fi

			echo "Installing from AUR: ${MISSING_AUR[*]}"
			$AUR_HELPER -S --needed --noconfirm "${MISSING_AUR[@]}"
		fi

	elif command -v apt-get &>/dev/null; then
		# Debian/Ubuntu
		echo "Installing tools via apt..."
		sudo apt-get update

		# Map tool names to package names
		APT_PACKAGES=()
		for tool in "${MISSING_TOOLS[@]}"; do
			case $tool in
			ctags) APT_PACKAGES+=("universal-ctags") ;;
			ugrep) APT_PACKAGES+=("ugrep") ;;
			*) APT_PACKAGES+=("$tool") ;;
			esac
		done

		[ ${#APT_PACKAGES[@]} -gt 0 ] && sudo apt-get install -y "${APT_PACKAGES[@]}"

		# Install tokei/scc via cargo or snap
		for aur_tool in "${MISSING_AUR[@]}"; do
			if command -v cargo &>/dev/null; then
				echo "Installing $aur_tool via cargo..."
				cargo install "$aur_tool"
			elif command -v snap &>/dev/null; then
				echo "Installing $aur_tool via snap..."
				sudo snap install "$aur_tool"
			else
				echo -e "${YELLOW}Warning: Cannot install $aur_tool. Install cargo or snap first.${NC}"
			fi
		done

	elif command -v dnf &>/dev/null; then
		# Fedora
		echo "Installing tools via dnf..."
		sudo dnf install -y "${MISSING_TOOLS[@]}" "${MISSING_AUR[@]}" 2>/dev/null || {
			# tokei/scc might need cargo
			for aur_tool in "${MISSING_AUR[@]}"; do
				if command -v cargo &>/dev/null; then
					cargo install "$aur_tool"
				fi
			done
		}

	elif command -v brew &>/dev/null; then
		# macOS with Homebrew
		echo "Installing tools via brew..."
		ALL_TOOLS=("${MISSING_TOOLS[@]}" "${MISSING_AUR[@]}")
		brew install "${ALL_TOOLS[@]}"

	else
		echo -e "${RED}Unknown package manager. Please install these tools manually:${NC}"
		echo "  Official: ${MISSING_TOOLS[*]}"
		echo "  Additional: ${MISSING_AUR[*]}"
		exit 1
	fi

	echo -e "${GREEN}Tool installation complete.${NC}"
}

print_header "STEP 0: Checking/Installing Required Tools"
install_missing_tools

# Create directories
mkdir -p "$WORK_DIR" "$RESULTS_DIR"

#==============================================================================
# STEP 1: Clone or Use Local Repository
#==============================================================================
print_header "STEP 1: Repository Setup"

if [ "$IS_LOCAL" = true ]; then
	echo "Using local repository: $REPO_DIR"
	if [ ! -d "$REPO_DIR" ]; then
		echo "Error: Directory does not exist: $REPO_DIR"
		exit 1
	fi
else
	# Remote URL - clone it
	if [ -d "$REPO_DIR" ]; then
		echo "Repository already exists at $REPO_DIR"
		echo "Updating..."
		cd "$REPO_DIR"
		git pull --depth 1 2>/dev/null || echo "Update skipped (shallow clone)"
	else
		echo "Cloning $REPO_URL (shallow clone for speed)..."
		git clone --depth 1 "$REPO_URL" "$REPO_DIR"
	fi
fi

cd "$REPO_DIR"
echo "Repository: $REPO_NAME"
echo "Location: $REPO_DIR"
echo "Repository size: $(du -sh . | cut -f1)"
if [ "$RESPECT_GITIGNORE" = true ] && is_git_repo; then
	# Count files respecting .gitignore
	FILE_COUNT=$({
		git ls-files 2>/dev/null
		git ls-files --others --exclude-standard 2>/dev/null
	} | sort -u | wc -l)
	echo "Files: $FILE_COUNT (respecting .gitignore)"
elif [ "$RESPECT_GITIGNORE" = true ]; then
	echo "Files: $(find . -type f 2>/dev/null | grep -Ev "/($EXCLUDE_DIRS)/" | wc -l) (excluding common dirs)"
else
	echo "Files: $(find . -type f | wc -l)"
fi

#==============================================================================
# STEP 2: Basic Statistics with tokei
#==============================================================================
print_header "STEP 2: Code Statistics with tokei"

echo "Running tokei..."
tokei . | tee "$RESULTS_DIR/tokei_stats.txt"

#==============================================================================
# STEP 3: Code Statistics with scc
#==============================================================================
print_header "STEP 3: Code Statistics with scc (includes complexity)"

echo "Running scc..."
scc . | tee "$RESULTS_DIR/scc_stats.txt"

print_subheader "Top 10 Most Complex Files"
scc --by-file --sort complexity . 2>/dev/null | head -20 | tee "$RESULTS_DIR/scc_complexity.txt"

#==============================================================================
# STEP 4: Fast Keyword Analysis (Code vs Comments) - Multi-Language
#==============================================================================
print_header "STEP 4: Fast Keyword Analysis (Code vs Comments)"

# Helper function for fast word counting
# Uses 'counts' (Rust) if available, falls back to Python Counter
fast_count() {
	local top_n="${1:-50}"
	if command -v counts &>/dev/null; then
		counts 2>/dev/null | head -$((top_n + 1)) | tail -$top_n
	else
		python3 -c "
import sys
from collections import Counter
c = Counter(line.rstrip() for line in sys.stdin)
for word, count in c.most_common($top_n):
    print(f'{count} {word}')
"
	fi
}

#------------------------------------------------------------------------------
# Language Detection and Configuration
#------------------------------------------------------------------------------
print_subheader "Detecting languages in repository..."

if [ "$RESPECT_GITIGNORE" = true ]; then
	if is_git_repo; then
		echo -e "${YELLOW}Note: Respecting .gitignore (excludes node_modules, build outputs, etc.)${NC}"
	else
		echo -e "${YELLOW}Note: Excluding common directories (node_modules, .git, vendor, etc.)${NC}"
	fi
	echo "      Use --no-ignore to include everything."
	echo ""
fi

# Count files by extension to detect primary languages (using helper)
declare -A LANG_FILES
LANG_FILES[c]=$(count_files "*.c")
LANG_FILES[cpp]=$(count_files "*.cpp" "*.cc" "*.cxx")
LANG_FILES[h]=$(count_files "*.h" "*.hpp" "*.hxx")
LANG_FILES[python]=$(count_files "*.py")
LANG_FILES[javascript]=$(count_files "*.js")
LANG_FILES[typescript]=$(count_files "*.ts" "*.tsx")
LANG_FILES[java]=$(count_files "*.java")
LANG_FILES[go]=$(count_files "*.go")
LANG_FILES[rust]=$(count_files "*.rs")
LANG_FILES[ruby]=$(count_files "*.rb")
LANG_FILES[shell]=$(count_files "*.sh" "*.bash")

echo "Files found by language:"
for lang in c cpp h python javascript typescript java go rust ruby shell; do
	count=${LANG_FILES[$lang]}
	[ "$count" -gt 0 ] && echo "  $lang: $count files"
done

# Determine which language families are present
HAS_C_FAMILY=false
HAS_PYTHON=false
HAS_JS_FAMILY=false
HAS_SHELL=false
HAS_RUBY=false
HAS_GO=false
HAS_RUST=false
HAS_JAVA=false

((${LANG_FILES[c]} + ${LANG_FILES[cpp]} + ${LANG_FILES[h]} > 0)) && HAS_C_FAMILY=true
((${LANG_FILES[python]} > 0)) && HAS_PYTHON=true
((${LANG_FILES[javascript]} + ${LANG_FILES[typescript]} > 0)) && HAS_JS_FAMILY=true
((${LANG_FILES[shell]} > 0)) && HAS_SHELL=true
((${LANG_FILES[ruby]} > 0)) && HAS_RUBY=true
((${LANG_FILES[go]} > 0)) && HAS_GO=true
((${LANG_FILES[rust]} > 0)) && HAS_RUST=true
((${LANG_FILES[java]} > 0)) && HAS_JAVA=true

#------------------------------------------------------------------------------
# Language-specific keyword definitions
#------------------------------------------------------------------------------
# C/C++ keywords
KEYWORDS_C="auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|int|long|register|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while|inline|restrict|_Bool|_Complex|_Imaginary"
KEYWORDS_CPP="$KEYWORDS_C|alignas|alignof|and|and_eq|asm|atomic_cancel|atomic_commit|atomic_noexcept|bitand|bitor|bool|catch|char16_t|char32_t|char8_t|class|co_await|co_return|co_yield|compl|concept|const_cast|consteval|constexpr|constinit|decltype|delete|dynamic_cast|explicit|export|false|friend|mutable|namespace|new|noexcept|not|not_eq|nullptr|operator|or|or_eq|override|private|protected|public|reflexpr|reinterpret_cast|requires|static_assert|static_cast|synchronized|template|this|thread_local|throw|true|try|typeid|typename|using|virtual|wchar_t|xor|xor_eq"

# Python keywords
KEYWORDS_PYTHON="False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield"

# JavaScript/TypeScript keywords
KEYWORDS_JS="abstract|arguments|await|boolean|break|byte|case|catch|char|class|const|continue|debugger|default|delete|do|double|else|enum|eval|export|extends|false|final|finally|float|for|function|goto|if|implements|import|in|instanceof|int|interface|let|long|native|new|null|package|private|protected|public|return|short|static|super|switch|synchronized|this|throw|throws|transient|true|try|typeof|undefined|var|void|volatile|while|with|yield"
KEYWORDS_TS="$KEYWORDS_JS|any|as|asserts|bigint|declare|get|infer|intrinsic|is|keyof|module|namespace|never|out|override|readonly|require|set|string|symbol|type|unique|unknown"

# Go keywords
KEYWORDS_GO="break|case|chan|const|continue|default|defer|else|fallthrough|for|func|go|goto|if|import|interface|map|package|range|return|select|struct|switch|type|var"

# Rust keywords
KEYWORDS_RUST="as|async|await|break|const|continue|crate|dyn|else|enum|extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|ref|return|self|Self|static|struct|super|trait|true|type|unsafe|use|where|while"

# Ruby keywords
KEYWORDS_RUBY="BEGIN|END|alias|and|begin|break|case|class|def|defined|do|else|elsif|end|ensure|false|for|if|in|module|next|nil|not|or|redo|rescue|retry|return|self|super|then|true|undef|unless|until|when|while|yield"
#------------------------------------------------------------------------------
# Multi-language comment processing - KEEP LANGUAGES SEPARATE
#------------------------------------------------------------------------------
print_subheader "Processing source files (separating code from comments)..."

# Create per-language output directory
mkdir -p "$RESULTS_DIR/per_language"
COMMENTS_TEMP=$(mktemp)
trap 'rm -f "$COMMENTS_TEMP" /tmp/code_*.tmp 2>/dev/null' EXIT

declare -A LANG_CODE_FILES

# Process C/C++ files
if $HAS_C_FAMILY; then
	echo "Processing C/C++ files..."
	LANG_CODE_FILES[c_cpp]=$(mktemp /tmp/code_c_cpp.XXXXXX.tmp)
	find_files "*.c" "*.cpp" "*.cc" "*.cxx" "*.h" "*.hpp" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[c_cpp]}"

	# Extract and strip C-style comments
	perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[c_cpp]}" >>"$COMMENTS_TEMP"
	perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[c_cpp]}" >"${LANG_CODE_FILES[c_cpp]}.clean"
	mv "${LANG_CODE_FILES[c_cpp]}.clean" "${LANG_CODE_FILES[c_cpp]}"
fi

# Process JavaScript files (separate from TypeScript)
if $HAS_JS_FAMILY; then
	echo "Processing JavaScript files..."
	LANG_CODE_FILES[javascript]=$(mktemp /tmp/code_js.XXXXXX.tmp)
	find_files "*.js" "*.jsx" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[javascript]}"

	echo "Processing TypeScript files..."
	LANG_CODE_FILES[typescript]=$(mktemp /tmp/code_ts.XXXXXX.tmp)
	find_files "*.ts" "*.tsx" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[typescript]}"

	# Extract and strip comments from both
	for lang_file in "${LANG_CODE_FILES[javascript]}" "${LANG_CODE_FILES[typescript]}"; do
		[ ! -s "$lang_file" ] && continue
		perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "$lang_file" >>"$COMMENTS_TEMP"
		perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "$lang_file" >"${lang_file}.clean"
		mv "${lang_file}.clean" "$lang_file"
	done
fi

# Process Python files
if $HAS_PYTHON; then
	echo "Processing Python files..."
	LANG_CODE_FILES[python]=$(mktemp /tmp/code_python.XXXXXX.tmp)
	find_files "*.py" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[python]}"

	perl -ne 'if (/^\s*#(.*)/) { print "$1\n"; } elsif (/#(.*)$/) { print "$1\n"; }' "${LANG_CODE_FILES[python]}" >>"$COMMENTS_TEMP"
	perl -0777 -ne 'while (/"""(.+?)"""/gs) { print "$1\n"; } while (/'"'"''"'"''"'"'(.+?)'"'"''"'"''"'"'/gs) { print "$1\n"; }' "${LANG_CODE_FILES[python]}" >>"$COMMENTS_TEMP"
	perl -pe 's/#.*$//' "${LANG_CODE_FILES[python]}" | perl -0777 -pe 's/""".*?"""//gs; s/'"'"''"'"''"'"'.*?'"'"''"'"''"'"'//gs' >"${LANG_CODE_FILES[python]}.clean"
	mv "${LANG_CODE_FILES[python]}.clean" "${LANG_CODE_FILES[python]}"
fi

# Process Go files
if $HAS_GO; then
	echo "Processing Go files..."
	LANG_CODE_FILES[go]=$(mktemp /tmp/code_go.XXXXXX.tmp)
	find_files "*.go" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[go]}"

	perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[go]}" >>"$COMMENTS_TEMP"
	perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[go]}" >"${LANG_CODE_FILES[go]}.clean"
	mv "${LANG_CODE_FILES[go]}.clean" "${LANG_CODE_FILES[go]}"
fi

# Process Rust files
if $HAS_RUST; then
	echo "Processing Rust files..."
	LANG_CODE_FILES[rust]=$(mktemp /tmp/code_rust.XXXXXX.tmp)
	find_files "*.rs" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[rust]}"

	perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[rust]}" >>"$COMMENTS_TEMP"
	perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[rust]}" >"${LANG_CODE_FILES[rust]}.clean"
	mv "${LANG_CODE_FILES[rust]}.clean" "${LANG_CODE_FILES[rust]}"
fi

# Process Ruby files
if $HAS_RUBY; then
	echo "Processing Ruby files..."
	LANG_CODE_FILES[ruby]=$(mktemp /tmp/code_ruby.XXXXXX.tmp)
	find_files "*.rb" | head -5000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[ruby]}"

	perl -ne 'if (/#(.*)$/) { print "$1\n"; }' "${LANG_CODE_FILES[ruby]}" >>"$COMMENTS_TEMP"
	perl -0777 -ne 'while (/=begin(.+?)=end/gs) { print "$1\n"; }' "${LANG_CODE_FILES[ruby]}" >>"$COMMENTS_TEMP"
	perl -pe 's/#.*$//' "${LANG_CODE_FILES[ruby]}" | perl -0777 -pe 's/=begin.*?=end//gs' >"${LANG_CODE_FILES[ruby]}.clean"
	mv "${LANG_CODE_FILES[ruby]}.clean" "${LANG_CODE_FILES[ruby]}"
fi

# Process Shell files
if $HAS_SHELL; then
	echo "Processing Shell files..."
	LANG_CODE_FILES[shell]=$(mktemp /tmp/code_shell.XXXXXX.tmp)
	find_files "*.sh" "*.bash" | head -5000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[shell]}"

	perl -ne 'if (/^\s*#(.*)/ && !/^#!/) { print "$1\n"; } elsif (/#(.*)$/) { print "$1\n"; }' "${LANG_CODE_FILES[shell]}" >>"$COMMENTS_TEMP"
	perl -pe 's/#.*$//' "${LANG_CODE_FILES[shell]}" >"${LANG_CODE_FILES[shell]}.clean"
	mv "${LANG_CODE_FILES[shell]}.clean" "${LANG_CODE_FILES[shell]}"
fi

# Process Java files
if $HAS_JAVA; then
	echo "Processing Java files..."
	LANG_CODE_FILES[java]=$(mktemp /tmp/code_java.XXXXXX.tmp)
	find_files "*.java" | head -15000 | xargs cat 2>/dev/null >"${LANG_CODE_FILES[java]}"

	perl -0777 -ne 'while (/\/\*(.+?)\*\//gs) { print "$1\n"; } while (/\/\/([^\n]*)/g) { print "$1\n"; }' "${LANG_CODE_FILES[java]}" >>"$COMMENTS_TEMP"
	perl -0777 -pe 's|/\*.*?\*/||gs; s|//[^\n]*||g;' "${LANG_CODE_FILES[java]}" >"${LANG_CODE_FILES[java]}.clean"
	mv "${LANG_CODE_FILES[java]}.clean" "${LANG_CODE_FILES[java]}"
fi

COMMENT_LINES=$(wc -l <"$COMMENTS_TEMP")
echo ""
echo "Processed languages: ${!LANG_CODE_FILES[*]}"
echo "Total comment lines: $COMMENT_LINES"

#------------------------------------------------------------------------------
# Per-Language Keyword Analysis - Each language gets its own file
#------------------------------------------------------------------------------
print_subheader "Per-Language Keyword Analysis"

# Map language names to keyword variables
declare -A LANG_KEYWORDS
LANG_KEYWORDS[c_cpp]="$KEYWORDS_CPP"
LANG_KEYWORDS[python]="$KEYWORDS_PYTHON"
LANG_KEYWORDS[javascript]="$KEYWORDS_JS"
LANG_KEYWORDS[typescript]="$KEYWORDS_TS"
LANG_KEYWORDS[go]="$KEYWORDS_GO"
LANG_KEYWORDS[rust]="$KEYWORDS_RUST"
LANG_KEYWORDS[ruby]="$KEYWORDS_RUBY"
LANG_KEYWORDS[shell]="$KEYWORDS_SHELL"
LANG_KEYWORDS[java]="$KEYWORDS_JAVA"

# Analyze each language separately
for lang in "${!LANG_CODE_FILES[@]}"; do
	code_file="${LANG_CODE_FILES[$lang]}"
	keywords="${LANG_KEYWORDS[$lang]}"
	output_file="$RESULTS_DIR/per_language/keywords_${lang}.txt"

	if [ -f "$code_file" ] && [ -s "$code_file" ] && [ -n "$keywords" ]; then
		echo ""
		echo -e "${YELLOW}=== $lang Keywords ===${NC}"
		ugrep -o "\b($keywords)\b" "$code_file" 2>/dev/null |
			fast_count 50 |
			tee "$output_file"
	fi
done

#------------------------------------------------------------------------------
# Per-Language Function Analysis
#------------------------------------------------------------------------------
print_subheader "Per-Language Function Calls"

for lang in "${!LANG_CODE_FILES[@]}"; do
	code_file="${LANG_CODE_FILES[$lang]}"
	output_file="$RESULTS_DIR/per_language/functions_${lang}.txt"

	if [ -f "$code_file" ] && [ -s "$code_file" ]; then
		echo ""
		echo -e "${YELLOW}=== $lang Functions ===${NC}"
		ugrep -o '\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(' "$code_file" 2>/dev/null |
			sed 's/\s*(//' |
			grep -vE '^(if|for|while|switch|catch|elif)$' |
			fast_count 30 |
			tee "$output_file"
	fi
done

#------------------------------------------------------------------------------
# Per-Language Import Analysis
#------------------------------------------------------------------------------
print_subheader "Per-Language Imports/Includes"

# C/C++ includes
if [ -n "${LANG_CODE_FILES[c_cpp]}" ] && [ -s "${LANG_CODE_FILES[c_cpp]}" ]; then
	echo -e "${YELLOW}=== C/C++ Includes ===${NC}"
	ugrep -o '#include\s*[<"][^>"]+[>"]' "${LANG_CODE_FILES[c_cpp]}" 2>/dev/null |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_c_cpp.txt"
fi

# Python imports
if [ -n "${LANG_CODE_FILES[python]}" ] && [ -s "${LANG_CODE_FILES[python]}" ]; then
	echo ""
	echo -e "${YELLOW}=== Python Imports ===${NC}"
	ugrep -o '^\s*(from\s+\S+\s+import\s+\S+|import\s+\S+)' "${LANG_CODE_FILES[python]}" 2>/dev/null |
		sed 's/^\s*//' |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_python.txt"
fi

# JavaScript imports
if [ -n "${LANG_CODE_FILES[javascript]}" ] && [ -s "${LANG_CODE_FILES[javascript]}" ]; then
	echo ""
	echo -e "${YELLOW}=== JavaScript Imports ===${NC}"
	ugrep -o "(import\s+.*\s+from\s+['\"][^'\"]+['\"]|require\s*\(['\"][^'\"]+['\"]\))" "${LANG_CODE_FILES[javascript]}" 2>/dev/null |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_javascript.txt"
fi

# TypeScript imports
if [ -n "${LANG_CODE_FILES[typescript]}" ] && [ -s "${LANG_CODE_FILES[typescript]}" ]; then
	echo ""
	echo -e "${YELLOW}=== TypeScript Imports ===${NC}"
	ugrep -o "(import\s+.*\s+from\s+['\"][^'\"]+['\"]|require\s*\(['\"][^'\"]+['\"]\))" "${LANG_CODE_FILES[typescript]}" 2>/dev/null |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_typescript.txt"
fi

# Go imports
if [ -n "${LANG_CODE_FILES[go]}" ] && [ -s "${LANG_CODE_FILES[go]}" ]; then
	echo ""
	echo -e "${YELLOW}=== Go Imports ===${NC}"
	ugrep -o '"[^"]+/[^"]+"' "${LANG_CODE_FILES[go]}" 2>/dev/null |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_go.txt"
fi

# Rust use statements
if [ -n "${LANG_CODE_FILES[rust]}" ] && [ -s "${LANG_CODE_FILES[rust]}" ]; then
	echo ""
	echo -e "${YELLOW}=== Rust Use Statements ===${NC}"
	ugrep -o '^\s*use\s+[^;]+' "${LANG_CODE_FILES[rust]}" 2>/dev/null |
		sed 's/^\s*//' |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_rust.txt"
fi

# Java imports
if [ -n "${LANG_CODE_FILES[java]}" ] && [ -s "${LANG_CODE_FILES[java]}" ]; then
	echo ""
	echo -e "${YELLOW}=== Java Imports ===${NC}"
	ugrep -o '^\s*import\s+[^;]+' "${LANG_CODE_FILES[java]}" 2>/dev/null |
		sed 's/^\s*//' |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_java.txt"
fi

# Ruby requires
if [ -n "${LANG_CODE_FILES[ruby]}" ] && [ -s "${LANG_CODE_FILES[ruby]}" ]; then
	echo ""
	echo -e "${YELLOW}=== Ruby Requires ===${NC}"
	ugrep -o "(require\s+['\"][^'\"]+['\"]|require_relative\s+['\"][^'\"]+['\"])" "${LANG_CODE_FILES[ruby]}" 2>/dev/null |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_ruby.txt"
fi

# Shell sources
if [ -n "${LANG_CODE_FILES[shell]}" ] && [ -s "${LANG_CODE_FILES[shell]}" ]; then
	echo ""
	echo -e "${YELLOW}=== Shell Sources ===${NC}"
	ugrep -o '(source\s+[^\s]+|\.\s+[^\s]+)' "${LANG_CODE_FILES[shell]}" 2>/dev/null |
		fast_count 30 |
		tee "$RESULTS_DIR/per_language/imports_shell.txt"
fi

#------------------------------------------------------------------------------
# Combined Analysis (for overview/backward compatibility)
#------------------------------------------------------------------------------
print_subheader "Combined Code Identifiers (all languages)"

# Create combined CODE_TEMP
CODE_TEMP=$(mktemp)
for lang_file in "${LANG_CODE_FILES[@]}"; do
	[ -f "$lang_file" ] && cat "$lang_file" >>"$CODE_TEMP"
done

ugrep -o '\b[a-zA-Z_][a-zA-Z0-9_]*\b' "$CODE_TEMP" 2>/dev/null |
	fast_count $TOP_N |
	tee "$RESULTS_DIR/code_identifiers.txt"

print_subheader "Most Used Words in COMMENTS"
ugrep -o '\b[a-zA-Z_][a-zA-Z0-9_]*\b' "$COMMENTS_TEMP" 2>/dev/null |
	fast_count $TOP_N |
	tee "$RESULTS_DIR/comment_words.txt"

# Create combined files from per-language analysis (for backward compatibility)
{
	echo "# Combined keywords from all languages"
	echo "# Format: count keyword (from per_language/keywords_*.txt)"
	cat "$RESULTS_DIR/per_language"/keywords_*.txt 2>/dev/null | grep -v '^$' | sort -t' ' -k1 -nr | head -100
} >"$RESULTS_DIR/grep_keywords.txt"

{
	echo "# Combined functions from all languages"
	echo "# See per_language/functions_*.txt for language-specific breakdown"
	cat "$RESULTS_DIR/per_language"/functions_*.txt 2>/dev/null | grep -v '^$' | sort -t' ' -k1 -nr | head -100
} >"$RESULTS_DIR/grep_function_calls.txt"

{
	echo "# Combined imports from all languages"
	echo "# See per_language/imports_*.txt for language-specific breakdown"
	cat "$RESULTS_DIR/per_language"/imports_*.txt 2>/dev/null | grep -v '^$' | sort -t' ' -k1 -nr | head -100
} >"$RESULTS_DIR/grep_imports.txt"

# List what per-language files were created
echo ""
echo "Per-language analysis files created:"
find "$RESULTS_DIR/per_language/" -maxdepth 1 -type f -printf '  %f\n' 2>/dev/null || true

print_subheader "Generating tags (this may take a while)..."

# Generate tags for different kinds
ctags -R --languages=C,C++ --c-kinds=+fp --fields=+lK -f "$RESULTS_DIR/tags" . 2>/dev/null || true

if [ -f "$RESULTS_DIR/tags" ]; then
	TOTAL_TAGS=$(grep -ac '^[^!]' "$RESULTS_DIR/tags" 2>/dev/null || echo "0")
	echo "Total symbols found: $TOTAL_TAGS"

	print_subheader "Most Common Symbol Names"
	# Fast: use cut + counts instead of awk + sort | uniq
	# -a flag treats tags file as text (may contain binary-like patterns)
	grep -a '^[^!]' "$RESULTS_DIR/tags" | cut -f1 | fast_count $TOP_N |
		tee "$RESULTS_DIR/ctags_symbols.txt"

	print_subheader "Symbol Types Distribution"
	# Fast: extract single-letter kind code after ;" and count
	grep -aoP ';"\t\K[a-z]' "$RESULTS_DIR/tags" 2>/dev/null | fast_count 20 | while read count kind; do
		case $kind in
		f) echo "$count functions" ;;
		v) echo "$count variables" ;;
		s) echo "$count structs" ;;
		t) echo "$count typedefs" ;;
		e) echo "$count enum values" ;;
		g) echo "$count enums" ;;
		m) echo "$count struct/union members" ;;
		d) echo "$count macro definitions" ;;
		p) echo "$count function prototypes" ;;
		u) echo "$count unions" ;;
		c) echo "$count classes" ;;
		n) echo "$count namespaces" ;;
		*) echo "$count kind=$kind" ;;
		esac
	done | tee "$RESULTS_DIR/ctags_kinds.txt"
fi

#==============================================================================
# STEP 6: cscope Analysis
#==============================================================================
print_header "STEP 6: cscope Database Analysis"

print_subheader "Building cscope database..."

# Find all C source files (respecting .gitignore if available)
if [ "$RESPECT_GITIGNORE" = true ] && is_git_repo; then
	{
		git ls-files -- '*.c' '*.h' 2>/dev/null
		git ls-files --others --exclude-standard -- '*.c' '*.h' 2>/dev/null
	} | sort -u >"$RESULTS_DIR/cscope.files"
elif [ "$RESPECT_GITIGNORE" = true ]; then
	find . \( -name "*.c" -o -name "*.h" \) -type f 2>/dev/null | grep -Ev "/($EXCLUDE_DIRS)/" >"$RESULTS_DIR/cscope.files"
else
	find . \( -name "*.c" -o -name "*.h" \) -type f >"$RESULTS_DIR/cscope.files" 2>/dev/null
fi
FILE_COUNT=$(wc -l <"$RESULTS_DIR/cscope.files")
echo "Found $FILE_COUNT source files"

# Build cscope database (can take a while for large repos)
echo "Building database (this may take several minutes for Linux kernel)..."
cscope -b -q -i "$RESULTS_DIR/cscope.files" -f "$RESULTS_DIR/cscope.out" 2>/dev/null || true

if [ -f "$RESULTS_DIR/cscope.out" ]; then
	echo "Database built successfully"
	echo "Database size: $(du -sh "$RESULTS_DIR/cscope.out" | cut -f1)"

	print_subheader "Example: Finding callers of 'printk' function"
	cscope -d -f "$RESULTS_DIR/cscope.out" -L -3 printk 2>/dev/null | head -20 || echo "No results"

	print_subheader "Example: Finding definition of 'struct file'"
	cscope -d -f "$RESULTS_DIR/cscope.out" -L -1 "struct file" 2>/dev/null | head -10 || echo "No results"
fi

#==============================================================================
# STEP 7: clang AST Analysis (if available)
#==============================================================================
print_header "STEP 7: clang-based Analysis (AST-level)"

print_subheader "Analyzing a sample file with clang AST dump"

# Find a simple C file to analyze (respecting .gitignore)
if [ "$RESPECT_GITIGNORE" = true ] && is_git_repo; then
	SAMPLE_FILE=$(git ls-files -- '*.c' 2>/dev/null | head -20 | while read -r f; do
		[ -f "$f" ] && [ "$(stat -c%s "$f" 2>/dev/null || echo 999999)" -lt 51200 ] && echo "$f"
	done | head -1)
elif [ "$RESPECT_GITIGNORE" = true ]; then
	SAMPLE_FILE=$(find . -name "*.c" -size -50k -type f 2>/dev/null | grep -Ev "/($EXCLUDE_DIRS)/" | head -1)
else
	SAMPLE_FILE=$(find . -name "*.c" -size -50k 2>/dev/null | head -1)
fi

if [ -n "$SAMPLE_FILE" ]; then
	echo "Sample file: $SAMPLE_FILE"
	echo ""
	echo "Function declarations in this file:"
	clang -Xclang -ast-dump -fsyntax-only "$SAMPLE_FILE" 2>/dev/null |
		grep -E "FunctionDecl.*<.*>" |
		head -20 |
		sed 's/.*FunctionDecl.*<[^>]*> /  /' |
		tee "$RESULTS_DIR/clang_sample_functions.txt" || echo "Analysis failed (missing headers)"
fi

print_subheader "Note: Full clang analysis requires compile_commands.json"
echo "For proper AST analysis of the Linux kernel, you need to:"
echo "  1. Configure the kernel: make defconfig"
echo "  2. Generate compile_commands.json: make compile_commands.json"
echo "  3. Use clang-query or clang-check with the database"

#==============================================================================
# STEP 8: Summary
#==============================================================================
print_header "ANALYSIS COMPLETE"

echo "Results saved to: $RESULTS_DIR/"
echo ""
ls -la "$RESULTS_DIR/"

echo ""
echo -e "${GREEN}Quick Summary:${NC}"
echo ""

if [ -f "$RESULTS_DIR/grep_keywords.txt" ]; then
	echo "Top 5 Language Keywords (in code):"
	head -5 "$RESULTS_DIR/grep_keywords.txt" | awk '{printf "  %s: %s times\n", $2, $1}'
fi

echo ""
if [ -f "$RESULTS_DIR/grep_function_calls.txt" ]; then
	echo "Top 5 Function/Method Calls (in code):"
	head -5 "$RESULTS_DIR/grep_function_calls.txt" | awk '{printf "  %s(): %s times\n", $2, $1}'
fi

echo ""
if [ -f "$RESULTS_DIR/comment_words.txt" ]; then
	echo "Top 5 Words in Comments:"
	head -5 "$RESULTS_DIR/comment_words.txt" | awk '{printf "  %s: %s times\n", $2, $1}'
fi

echo ""
if [ -f "$RESULTS_DIR/grep_imports.txt" ]; then
	echo "Top 5 Imports/Includes:"
	head -5 "$RESULTS_DIR/grep_imports.txt" | awk '{count=$1; $1=""; printf "  %s: %s times\n", substr($0,2), count}'
fi

echo ""
echo -e "${BLUE}To explore interactively with cscope (C/C++ only):${NC}"
echo "  cd $REPO_DIR && cscope -d -f $RESULTS_DIR/cscope.out"
echo ""
echo -e "${BLUE}To browse tags in vim:${NC}"
echo "  cd $REPO_DIR && vim -t main"
