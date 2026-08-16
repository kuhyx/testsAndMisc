#!/bin/bash

# ==============================================================================
# The full-mode linters: everything that runs after --quick would have exited.
#
# Split out of lint_python.sh for the 250-line cap. Each block is guarded by
# check_tool, so a missing linter is skipped rather than fatal. Reads
# TARGET_FILES / FIX_MODE and sets OVERALL_STATUS in the caller's scope.
# ==============================================================================

# shellcheck shell=bash

# Declared here so shellcheck can see that these cross the seam: the caller
# owns them, this file reads TARGET_FILES/FIX_MODE/REPORT_MODE and writes
# OVERALL_STATUS back. Without the declaration shellcheck analyses this file
# standalone and reports OVERALL_STATUS as unused (SC2034).
: "${TARGET_FILES:=}" "${FIX_MODE:=false}" "${REPORT_MODE:=false}"
OVERALL_STATUS="${OVERALL_STATUS:-0}"

run_full_mode_linters() {
	# ==============================================================================
	# PYLINT - Comprehensive linting
	# ==============================================================================
	if check_tool pylint; then
		run_tool "pylint" "pylint --rcfile=pyproject.toml --jobs=0 --fail-under=10 ${TARGET_FILES}" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# BANDIT - Security linting
	# ==============================================================================
	if check_tool bandit; then
		run_tool "bandit" "bandit -c pyproject.toml -r ${TARGET_FILES} --severity-level low --confidence-level low" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# VULTURE - Dead code detection
	# ==============================================================================
	if check_tool vulture; then
		run_tool "vulture" "vulture --min-confidence 80 ${TARGET_FILES}" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# FLAKE8 - Traditional linter
	# ==============================================================================
	if check_tool flake8; then
		run_tool "flake8" "flake8 --max-line-length=88 --extend-ignore=E203,W503 --max-complexity=10 ${TARGET_FILES}" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# PYCODESTYLE - PEP 8 style checker
	# ==============================================================================
	if check_tool pycodestyle; then
		run_tool "pycodestyle" "pycodestyle --max-line-length=88 --ignore=E203,W503 ${TARGET_FILES}" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# PYDOCSTYLE - Docstring style checker
	# ==============================================================================
	if check_tool pydocstyle; then
		run_tool "pydocstyle" "pydocstyle --convention=google ${TARGET_FILES}" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# RADON - Complexity metrics
	# ==============================================================================
	if check_tool radon; then
		print_subheader "Running radon (complexity analysis)..."
		echo ""
		echo -e "${MAGENTA}Cyclomatic Complexity:${NC}"
		radon cc -a -s "${TARGET_FILES_ARR[@]}" || true
		echo ""
		echo -e "${MAGENTA}Maintainability Index:${NC}"
		radon mi -s "${TARGET_FILES_ARR[@]}" || true

		if [[ "${REPORT_MODE}" == true ]]; then
			radon cc -a -s "${TARGET_FILES_ARR[@]}" >"${PROJECT_ROOT}/lint-reports/radon-cc.txt" 2>&1 || true
			radon mi -s "${TARGET_FILES_ARR[@]}" >"${PROJECT_ROOT}/lint-reports/radon-mi.txt" 2>&1 || true
		fi
	fi

	# ==============================================================================
	# INTERROGATE - Docstring coverage
	# ==============================================================================
	if check_tool interrogate; then
		run_tool "interrogate" "interrogate -v --fail-under=0 ${TARGET_FILES}" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# PYRIGHT - Microsoft's type checker (optional, very strict)
	# ==============================================================================
	if check_tool pyright; then
		run_tool "pyright" "pyright ${TARGET_FILES}" || OVERALL_STATUS=1
	fi

	# ==============================================================================
	# AUTOFLAKE - Unused imports/variables (fix mode only)
	# ==============================================================================
	if [[ "${FIX_MODE}" == true ]] && check_tool autoflake; then
		print_subheader "Running autoflake (removing unused imports)..."
		find "${TARGET_FILES_ARR[@]}" -name "*.py" -type f -exec autoflake --in-place --remove-all-unused-imports --remove-unused-variables {} \;
		print_success "autoflake completed"
	fi

	# ==============================================================================
	# PYUPGRADE - Upgrade Python syntax (fix mode only)
	# ==============================================================================
	if [[ "${FIX_MODE}" == true ]] && check_tool pyupgrade; then
		print_subheader "Running pyupgrade (upgrading syntax to Python 3.10+)..."
		find "${TARGET_FILES_ARR[@]}" -name "*.py" -type f -exec pyupgrade --py310-plus {} \;
		print_success "pyupgrade completed"
	fi

	# ==============================================================================
	# CODESPELL - Spell checking
	# ==============================================================================
	if check_tool codespell; then
		if [[ "${FIX_MODE}" == true ]]; then
			run_tool "codespell" "codespell -w --skip='*.json,*.lock,.git,__pycache__,.venv' ${TARGET_FILES}" || OVERALL_STATUS=1
		else
			run_tool "codespell" "codespell --skip='*.json,*.lock,.git,__pycache__,.venv' ${TARGET_FILES}" || OVERALL_STATUS=1
		fi
	fi
}
