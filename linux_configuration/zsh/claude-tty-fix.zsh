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
# Usage limit spent: when the statusLine cache says the 5-hour or 7-day window
# is at 100 % and has not reset yet, every claude / claude-* call below runs on
# the free models via `claude-free` instead (only where `free-llm-check-dir`
# allows it: public repos, /tmp, /var/log). `CLAUDE_USE_FREE=1` forces the free
# models; `CLAUDE_USE_FREE=0` keeps the real binary even with the limit spent.
# ============================================================================

# ----------------------------------------------------------------------------
# Safety net for the SIGTTIN-suspend case: when claude is *stopped* (not exited),
# the reset at the end of claude() below can NEVER run — the function is blocked
# inside `command claude`. So a suspended/killed claude leaves mouse tracking on
# and the terminal spews SGR mouse reports (e.g. `35;48;12M`). This precmd hook
# disables mouse tracking before every prompt, so the garble clears on your next
# Enter regardless of how claude died. Emits ONLY invisible mouse/cursor escapes
# (NOT bracketed-paste 2004, which zsh needs) so it can't disturb normal paste.
_claude_mouse_heal() {
    [[ -t 2 ]] || return
    printf '\e[?1000l\e[?1002l\e[?1003l\e[?1006l\e[?25h' > /dev/tty 2>/dev/null
}
autoload -Uz add-zsh-hook 2>/dev/null && add-zsh-hook precmd _claude_mouse_heal

# True when the newest limit-state shard (written by ~/.claude/scripts/statusline.sh;
# the limits are account-wide, so one file is enough) shows a window at 100 %
# whose reset time is still ahead. The `om[1]` glob qualifier picks the newest
# file without a fork; jq is the one fork, paid once per claude launch.
_claude_limit_spent() {
    local -a newest=("${LIMIT_STATE_DIR:-$HOME/.claude/cache/limit-state}"/*.json(N.om[1]))
    (( ${#newest} )) || return 1
    jq -e --argjson now "${EPOCHSECONDS:-$(date +%s)}" '
        def spent(p; r): ((.[p] // 0) >= 100) and ((.[r] // 0) > $now);
        spent("five_hour_pct"; "five_hour_resets_at")
        or spent("seven_day_pct"; "seven_day_resets_at")' -- "${newest[1]}" >/dev/null 2>&1
}

# Pick the binary: real claude, or claude-free once the usage limit is spent.
_claude_pick_cmd() {
    case "${CLAUDE_USE_FREE:-}" in
        0) reply=(command claude); return ;;
        ?*) reply=(claude-free); return ;;
    esac
    reply=(command claude)
    _claude_limit_spent || return 0
    free-llm-check-dir . 2>/dev/null || return 0
    print -ru2 -- "claude: usage limit spent, running claude-free (CLAUDE_USE_FREE=0 to skip)"
    reply=(claude-free)
}

claude() {
    # Escape sequences that undo the terminal state Claude may leave enabled if it
    # is stopped/killed before its own teardown runs:
    #   1000/1002/1003/1006 mouse tracking, 1004 focus reporting,
    #   2004 bracketed paste, 25 cursor visibility.
    local -r _claude_tty_reset=$'\e[?1000l\e[?1002l\e[?1003l\e[?1006l\e[?1004l\e[?2004l\e[?25h'

    # Route to the free models when the Claude usage limit is spent.
    local -a reply
    _claude_pick_cmd
    local -a _claude_cmd=("${reply[@]}")

    if [[ -n "${CLAUDE_TTY_FIX_OFF:-}" ]]; then
        "${_claude_cmd[@]}" "$@"
        return $?
    fi

    # `localoptions` confines the option change to this function; `nomonitor`
    # disables job control so claude shares the shell's (foreground) process group.
    setopt localoptions nomonitor

    # Always-on debug capture (turn off: `export CLAUDE_DEBUG_LOG_OFF=1`). The
    # trace goes to a FILE, not the screen, so the next real startup-race failure
    # is recorded faithfully — same wrapper, same env, same nomonitor, no
    # `script` surrogate to mask the job-control layer. Keeps the last ~20 logs.
    local _dbg=""
    if [[ -z "${CLAUDE_DEBUG_LOG_OFF:-}" ]]; then
        mkdir -p ~/.claude/logs 2>/dev/null
        _dbg=~/.claude/logs/claude-$(date +%Y%m%d-%H%M%S)-$$.log
        for f in ~/.claude/logs/claude-*.log(NOm[21,-1]); do rm -f -- "$f"; done
    fi

    if [[ -n "$_dbg" ]]; then
        "${_claude_cmd[@]}" --debug-file "$_dbg" "$@"
    else
        "${_claude_cmd[@]}" "$@"
    fi
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

# ============================================================================
# On-demand MCP servers — the niche fleet is NOT loaded every session.
# ----------------------------------------------------------------------------
# Only ~9 broadly-useful servers live in ~/.claude.json and start every time.
# The niche ones live in ~/.claude/mcp-optional/*.json and load only when you
# ask for them via `claude --mcp-config <file>` (the flag MERGES them into the
# global set for that one session). These wrappers call the `claude` FUNCTION
# above, so an on-demand session still gets the TTY fix + self-heal.
#   claude-rag     knowledge-rag + memstack-skills (data dirs pinned, no cwd litter)
#   claude-travel  wander-agent + airbnb
#   claude-sports  sports-hub + sportscore + rundida
#   claude-media   video-analyzer + nakkas + open-museum + go-docs
#   claude-extras  ALL of the above at once
# ============================================================================
claude-rag()    { claude --mcp-config ~/.claude/mcp-optional/rag.json "$@"; }
claude-travel() { claude --mcp-config ~/.claude/mcp-optional/travel.json "$@"; }
claude-sports() { claude --mcp-config ~/.claude/mcp-optional/sports.json "$@"; }
claude-media()  { claude --mcp-config ~/.claude/mcp-optional/media.json "$@"; }
claude-extras() { claude --mcp-config ~/.claude/mcp-optional/*.json "$@"; }

# ============================================================================
# claude-debug — RAW-binary A/B probe for the startup-interaction failure.
# ----------------------------------------------------------------------------
# Runs the real binary via `command` (bypassing the claude() wrapper, so NO
# nomonitor) in your real interactive shell, with --debug-file capturing Claude's
# timestamped startup trace to a file (off-screen). This tests whether the
# failure needs the wrapper's nomonitor or happens on the bare binary too.
# NOTE: do NOT wrap this in script(1) — script runs Claude without zsh job
# control, which MASKS the SIGTTIN suspend we are hunting.
# Usage: run `claude-debug`, TYPE during startup to trigger it, then IMMEDIATELY
# run `jobs -l` and tell me the exact text the shell printed, plus paste the log.
# ============================================================================
claude-debug() {
    mkdir -p ~/.claude/logs
    local dbg=~/.claude/logs/claude-RAW-$(date +%Y%m%d-%H%M%S)-$$.log
    print -r -- "→ RAW binary (no nomonitor), trace: $dbg"
    print -r -- "→ TYPE during startup to trigger it, then run: jobs -l"
    command claude --debug-file "$dbg" "$@"
    print -r -- "captured: $dbg  (exit=$?)"
}
