#!/usr/bin/env bash
# Block Python program logic embedded inline in a shell script.
#
# Inline Python is invisible to the repo's Python tooling: ruff, mypy, pylint,
# bandit and pytest all skip it, so it is the one place a type error or a
# security finding can live undetected. Extract it to a .py file under
# python_pkg/ and invoke it as `python3 "$(dirname "$0")/helper.py" "$arg"`.
#
# Permitted, and deliberately not flagged: a SINGLE-LINE availability or
# version probe with no logic, e.g.
#   python3 -c 'import kasa'
#   python -c "import sys; print(sys.version_info[0])"
# These carry no logic worth linting -- they are a yes/no question about the
# interpreter, and extracting them to a file would be sillier than inlining.
#
# Used as a pre-commit hook; receives staged file paths as arguments.

set -uo pipefail

errors=()

# A `python <<EOF` / `python3 <<-'PY'` heredoc: always real logic, never a
# probe. Matches an optional redirect target so `python3 <<'PY' >out` is caught.
readonly HEREDOC_RE='(^|[^[:alnum:]_])python3?[[:space:]]+<<-?'

# The opening of a `python -c "` whose closing quote is NOT on the same line,
# i.e. a multi-line inline program. A single-line -c closes its own quote and
# so does not match.
readonly MULTILINE_C_RE='(^|[^[:alnum:]_])python3?[[:space:]]+(-[[:alnum:]]+[[:space:]]+)*-c[[:space:]]*("[^"]*$|'"'"'[^'"'"']*$)'

for file in "$@"; do
    case "$file" in
        *.sh | *.bash | *.zsh) ;;
        *) continue ;;
    esac
    [[ -f "$file" ]] || continue

    while IFS=: read -r lineno text; do
        [[ -z "${lineno:-}" ]] && continue
        stripped="$(printf '%s' "$text" | sed 's/^[[:space:]]*//')"
        # A commented-out example is documentation, not shipped logic. Without
        # this, the rule's own explanatory comments would fail the hook.
        [[ "$stripped" == \#* ]] && continue
        errors+=("$file:$lineno: $stripped")
    done < <(grep -nE "$HEREDOC_RE|$MULTILINE_C_RE" "$file" 2>/dev/null || true)
done

if [[ ${#errors[@]} -gt 0 ]]; then
    echo "ERROR: Python program logic embedded in a shell script."
    echo "Inline Python is skipped by ruff, mypy, pylint, bandit and pytest."
    echo ""
    for err in "${errors[@]}"; do
        echo "  $err"
    done
    echo ""
    echo "Move the code to its own .py file and call it:"
    echo "  python3 \"\$(dirname \"\$0\")/helper.py\" \"\$arg\"    # bash"
    echo "  python3 \"\${0:A:h}/helper.py\" \"\$arg\"             # zsh"
    echo ""
    echo "A single-line probe such as python3 -c 'import kasa' is allowed."
    exit 1
fi
