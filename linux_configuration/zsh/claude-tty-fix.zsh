# ============================================================================
# claude-tty-fix.zsh — make Claude Code survive early typing in a fresh terminal
# ----------------------------------------------------------------------------
# Symptom this fixes:
#   Launch `claude` in a fresh terminal and type/interact during its ~5s startup
#   (instead of waiting) and the process stops with
#       [1] + <pid> suspended (tty input)
#   while the terminal spams sequences like `35;44;41M` (SGR mouse-motion
#   reports) and `997;1n` (the reply to Claude's dark-mode color-scheme probe).
#
# Why it happens (upstream, not our config):
#   Claude Code enables mouse tracking (\e[?1003h) and fires terminal-capability
#   probes the instant it starts. `suspended (tty input)` is a SIGTTIN job-control
#   stop: if the process is stopped mid-init, those terminal modes are never torn
#   down, so the shell — back in the foreground — echoes mouse movement and probe
#   replies as garbage. Known Claude Code bug, closed "not planned":
#   anthropics/claude-code #7807, #11898, #23581, #50032. No CLI flag / env var /
#   setting disables the mouse tracking or the probes, so we wrap the command.
#
# The wrapper does two things:
#   1. PREVENT the stop — run claude with zsh job-control monitoring off, so zsh
#      does not put it in its own background process group and it can never take
#      SIGTTIN. This is the only lever available outside the binary; whether it
#      fully prevents the stop is validated empirically (see the plan). Trade-off:
#      you cannot Ctrl-Z-suspend a claude session while this is active.
#   2. SELF-HEAL — on exit (however claude ended), disable the terminal modes it
#      may have left on and reset the line discipline, so a garble never persists.
#
# Opt-out: `export CLAUDE_TTY_FIX_OFF=1` (falls back to the bare binary).
# ============================================================================

claude() {
    # Escape sequences that undo the terminal state Claude may leave enabled if it
    # is stopped/killed before its own teardown runs:
    #   1000/1002/1003/1006 mouse tracking, 1004 focus reporting,
    #   2004 bracketed paste, 25 cursor visibility.
    local -r _claude_tty_reset=$'\e[?1000l\e[?1002l\e[?1003l\e[?1006l\e[?1004l\e[?2004l\e[?25h'

    if [[ -n "${CLAUDE_TTY_FIX_OFF:-}" ]]; then
        command claude "$@"
        return $?
    fi

    # `localoptions` confines the option change to this function; `nomonitor`
    # disables job control so claude shares the shell's (foreground) process group.
    setopt localoptions nomonitor
    command claude "$@"
    local -r rc=$?

    # Only heal a real terminal, and write the reset to /dev/tty (the controlling
    # terminal) rather than stdout — otherwise headless/piped runs like
    # `claude -p '...' | jq` would get escape codes injected into their output.
    if [[ -t 1 || -t 2 ]]; then
        printf '%s' "$_claude_tty_reset" > /dev/tty 2>/dev/null
        stty sane < /dev/tty 2>/dev/null
    fi
    return $rc
}
