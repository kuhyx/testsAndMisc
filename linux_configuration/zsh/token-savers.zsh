# ============================================================================
# token-savers.zsh — run the session-autopsy compiled scripts WITHOUT Claude.
# The deterministic 90% of these workflows costs zero LLM tokens from a shell;
# bring Claude in only when a step fails and needs triage.
# Symlinked into ~/.oh-my-zsh/custom/ (house pattern, see claude-tty-fix.zsh).
# ============================================================================

# finish-gate [file...] — /finish's deterministic gate on the current repo:
# diff sizing, pre-commit (one autofix retry), tests. Exit 10/20 on failures.
finish-gate() { bash "$HOME/.claude/scripts/finish.sh" gate . "$@"; }

# phone-deploy [app-dir] [--release] — build + data-preserving install + launch
# + screenshot on the phone. Never uninstalls by construction.
phone-deploy() { bash "$HOME/.claude/scripts/phone_deploy.sh" "${1:-.}" "${@:2}"; }

# autopsy [subcommand ...] — the transcript analyzer; defaults to `report`.
# Try: autopsy candidates | autopsy measure | autopsy report --mark-reviewed
autopsy() { PYTHONPATH="$HOME/testsAndMisc" python3 -m python_pkg.session_autopsy "${1:-report}" "${@:2}"; }

# yay-clean [--dry-run] <pkg>...|--all — remove yay cache dirs plain rm chokes
# on (read-only fakeroot/Bazel trees). The cache was 314GB on 2026-07-24.
yay-clean() { bash "$HOME/.claude/scripts/yay_cache_clean.sh" "$@"; }
