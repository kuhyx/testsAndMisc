# ============================================================================
# calc-live.zsh — live "calculator as you type" for the zsh prompt
# ----------------------------------------------------------------------------
# Open a terminal and just type a math expression. The result appears, greyed,
# right after what you typed, updating on every keystroke. No "calc", no Enter.
#
#   2+2            =>  2+2 = 4
#   (5+3)/2        =>  (5+3)/2 = 4
#   1/3            =>  1/3 = 0.333333333333
#   sqrt(2)*3      =>  sqrt(2)*3 = 4.24264068712
#   sin(pi/2)      =>  sin(pi/2) = 1
#   2^10           =>  2^10 = 1024     (^ means power, calculator-style)
#
# Pressing Enter on a pure-math line prints "<expr> = <result>" instead of
# trying to run it as a command (so no "command not found"). History keeps the
# bare expression, not the print command.
#
# Only pure-math lines trigger this; normal commands (ls, git, cd ..) are left
# completely alone and never fork the evaluator.
#
# Richer math (units, hex, percentages): prefix the line with "=". These go to
# qalc (if installed) and update live too, via a warmed qalc coprocess:
#   =5 ft to cm    ->  5 ft to cm = 152.4 cm
#   =255 to hex    ->  255 to hex = 0xFF
#   =0xff + 1      ->  0xff + 1 = 256
#   =20% of 80     ->  20% of 80 = 16
# (The first "=" of a session spends ~120 ms warming qalc; after that ~1 ms.)
#
# Engine: a safe AST-based evaluator in the sibling calc_eval.py (~6 ms/eval),
# run via python3. It cannot import modules, touch files, or run arbitrary code,
# and a runaway expression (e.g. 9**9**9) is bounded by a power-exponent guard +
# CPU limit + timeout so it can never freeze the prompt.
#
# Disable for a session:  export CALC_LIVE_OFF=1   (then open a new shell)
# Remove permanently:     delete this file.
#
# NOTE: this widget manages POSTDISPLAY/region_highlight. If you ever enable
# the zsh-autosuggestions plugin (which also owns POSTDISPLAY), they will fight;
# revisit this then.
# ============================================================================

# Opt-out switch and a one-time guard against double loading.
[[ -n ${CALC_LIVE_OFF:-} ]] && return
[[ -n ${_CALC_LOADED:-} ]] && return
typeset -g _CALC_LOADED=1

# --- Pick the evaluator binary (prefer the fast system python over a shim) ---
if [[ -x /usr/bin/python3 ]]; then
  typeset -g _CALC_PY_BIN=/usr/bin/python3
else
  typeset -g _CALC_PY_BIN=${commands[python3]:-}
fi
typeset -g _CALC_TIMEOUT_BIN=${commands[timeout]:-}

# The safe AST evaluator lives under python_pkg/ so the repository's Python
# tooling (ruff, mypy, pylint, bandit, 100%-coverage tests) applies to it.
# Resolve it at source time: ${0:A} follows the oh-my-zsh symlink back to the
# real file in the repo; :h:h:h walks zsh/ -> linux_configuration/ -> repo root.
# ($0 inside a function would name the function, so capture it here.)
typeset -gr _CALC_EVAL_PY=${0:A:h:h:h}/python_pkg/live_calc/calc_eval.py

# Optional richer engine. qalc (libqalculate) handles units, hex, percentages
# and natural language, but its ~120 ms cold start is too slow to run on every
# keystroke, so it is used only for "="-prefixed lines, evaluated on Enter.
typeset -g _CALC_QALC_BIN=${commands[qalc]:-}

# No usable evaluator -> do nothing rather than half-installing.
[[ -n $_CALC_PY_BIN && -r $_CALC_EVAL_PY ]] || return

# --- Evaluate one expression; echoes the result, or nothing on failure -------
# Runs the standalone calc_eval.py. The expression is passed as argv[1]; the
# script reads it, evaluates it under CPU + wall-clock limits, and writes the
# formatted result (or nothing on any error / unsafe input / overflow / timeout).
_calc_eval() {
  emulate -L zsh
  local expr=$1 out
  # -S skips site init for a faster start; the outer `timeout` is a backstop in
  # case the script's own limits are unavailable on this platform.
  if [[ -n $_CALC_TIMEOUT_BIN ]]; then
    out=$("$_CALC_TIMEOUT_BIN" -k 0.1 0.5 "$_CALC_PY_BIN" -S "$_CALC_EVAL_PY" "$expr" 2>/dev/null)
  else
    out=$("$_CALC_PY_BIN" -S "$_CALC_EVAL_PY" "$expr" 2>/dev/null)
  fi
  print -r -- "$out"
}

# --- qalc (richer engine) for "="-prefixed lines: units, hex, percentages ----
# qalc cold start is ~120 ms, far too slow per keystroke; but a warmed qalc
# coprocess answers in ~1 ms, fast enough to evaluate live in the redraw hook.
# So we keep ONE persistent qalc per shell, started lazily on first "=" line.
#
# IMPORTANT: the coprocess lives in the main shell. Its evaluator must NOT be
# called via $(...) (that forks a subshell and loses the pipe) — it sets the
# global _CALC_QRESULT instead.
typeset -g  _CALC_QCO_UP=0       # 1 once the qalc coprocess is running
typeset -gi _CALC_QSEQ=0         # unique-sentinel counter (prevents desync)
typeset -g  _CALC_QEXPR=         # stripped expression from the last "=" line
typeset -g  _CALC_QRESULT=       # result from the last _calc_qalc_eval

# If the line is "=<expr>", set _CALC_QEXPR to the stripped <expr> and return 0.
_calc_qalc_line() {
  emulate -L zsh
  setopt local_options extended_glob
  local s=$1
  _CALC_QEXPR=
  [[ $s == (#s)[[:space:]]#=* ]] || return 1
  s=${s##[[:space:]]#=[[:space:]]#}   # drop leading spaces, the "=", trailing spaces
  [[ -n $s ]] || return 1
  _CALC_QEXPR=$s
  return 0
}

# Start / stop the persistent qalc coprocess (no job-control chatter).
_calc_qco_start() {
  setopt local_options no_monitor no_notify
  coproc "$_CALC_QALC_BIN" -t 2>/dev/null
  _CALC_QCO_PID=$!
  disown %+ 2>/dev/null
  _CALC_QCO_UP=1
}
_calc_qco_stop() {
  [[ ${_CALC_QCO_UP:-0} == 1 ]] || return 0
  kill "${_CALC_QCO_PID:-0}" 2>/dev/null
  _CALC_QCO_UP=0
}

# Evaluate _CALC_QEXPR (arg) via the coprocess; sets _CALC_QRESULT ("" on fail).
_calc_qalc_eval() {
  emulate -L zsh
  setopt local_options extended_glob no_monitor no_notify
  _CALC_QRESULT=
  [[ -n $_CALC_QALC_BIN ]] || return 0
  local expr=${1// of / * }                   # qalc mis-parses "A% of B"
  (( _CALC_QCO_UP )) || _calc_qco_start
  (( _CALC_QSEQ++ ))
  local sentinel="909090909${_CALC_QSEQ}"      # unique per call, echoes itself
  if ! { print -p -- "$expr" && print -p -- "$sentinel" } 2>/dev/null; then
    _calc_qco_stop; _calc_qco_start            # pipe broke -> restart once
    { print -p -- "$expr" && print -p -- "$sentinel" } 2>/dev/null || return 0
  fi
  local line result='' saw=0
  integer guard=0
  while (( guard++ < 100 )) && read -rp -t 0.8 line 2>/dev/null; do
    line=${line//$'\e'\[[0-9;?]##[a-zA-Z]/}    # strip color escapes
    line=${line##[[:space:]]##}; line=${line%%[[:space:]]##}
    [[ -z $line || $line == '>'* ]] && continue           # blank / echoed input
    [[ $line == *$sentinel* ]] && { saw=1; break; }         # our sentinel result
    result=$line
  done
  (( saw )) || { _CALC_QCO_UP=0; return 0 }     # timed out/wedged -> reset
  # qalc echoes the input back when it cannot evaluate (e.g. "1 / 0").
  [[ -n $result && ${result// /} != ${expr// /} ]] && _CALC_QRESULT=$result
  return 0
}

# --- Decide whether a line is a pure math expression worth evaluating --------
# Conservative on purpose: must contain a digit and an operator (or a function
# call), and consist only of math tokens. This keeps real commands untouched.
_calc_is_expr() {
  emulate -L zsh
  setopt local_options extended_glob
  local s=${1//[[:space:]]/}
  [[ -n $s ]] || return 1
  # Neutralise known function/constant words (longest first) so the remaining
  # text can be charset-checked as pure numeric/operator soup.
  local t=$s w
  for w in factorial asin acos atan sqrt sin cos tan log2 log ln exp \
           floor ceil gcd deg rad min max tau pi e; do
    t=${t//$w/0}
  done
  # Only digits, operators, parens, dot, comma may remain.
  # (Parens are backslash-escaped so the parser does not read them as a group.)
  [[ $t == [-0-9.,+*/%^\(\)]## ]] || return 1
  # Require a digit, and either an operator or a function call.
  [[ $s == *[0-9]* ]] || return 1
  [[ $s == *[-+*/%^]* || $s == *[a-z]*\(* ]] || return 1
  return 0
}

# --- ZLE plumbing ------------------------------------------------------------
typeset -g _CALC_LAST_BUFFER=$'\0'   # sentinel so the first redraw computes
typeset -g _CALC_LAST_RESULT=

# Drop our preview text and our highlight entry (leaving any others intact).
_calc_clear() {
  POSTDISPLAY=
  region_highlight=( "${(@)region_highlight:#*memo=calc*}" )
}

# Runs on every redraw; recomputes only when the buffer text actually changed.
_calc_preview() {
  emulate -L zsh
  [[ $BUFFER == $_CALC_LAST_BUFFER ]] && return
  _CALC_LAST_BUFFER=$BUFFER
  _CALC_LAST_RESULT=
  _calc_clear
  # "=<expr>" -> evaluate live with the warmed qalc coprocess (~1 ms).
  if [[ -n $_CALC_QALC_BIN ]] && _calc_qalc_line "$BUFFER"; then
    _calc_qalc_eval "$_CALC_QEXPR"
    if [[ -n $_CALC_QRESULT ]]; then
      _CALC_LAST_RESULT=$_CALC_QRESULT
      POSTDISPLAY=" = $_CALC_QRESULT"
    else
      POSTDISPLAY="  …"          # typed so far is not yet a complete expression
    fi
    region_highlight+=("${#BUFFER} $((${#BUFFER} + ${#POSTDISPLAY})) fg=242,memo=calc")
    return
  fi
  _calc_is_expr "$BUFFER" || return
  local r
  r=$(_calc_eval "$BUFFER")
  [[ -n $r && $r != $BUFFER ]] || return
  _CALC_LAST_RESULT=$r
  POSTDISPLAY=" = $r"
  region_highlight+=("${#BUFFER} $((${#BUFFER} + ${#POSTDISPLAY})) fg=242,memo=calc")
}

# Result waiting to be printed to scrollback by the next precmd.
typeset -g _CALC_PENDING=

# Print the accepted calculation just before the next prompt is drawn, so it
# lands in scrollback exactly where command output would.
_calc_flush() {
  if [[ -n $_CALC_PENDING ]]; then
    print -r -- "$_CALC_PENDING"
    _CALC_PENDING=
  fi
}

# Enter on a pure-math line: record the result for printing, keep the bare
# expression in history, and execute nothing (so no "command not found").
_calc_accept_line() {
  emulate -L zsh
  if [[ -n $_CALC_QALC_BIN ]] && _calc_qalc_line "$BUFFER"; then
    # "=<expr>" -> reuse the live coprocess result (recompute only if stale).
    # Never execute a "=" line as a command, even if qalc returns nothing.
    local r=$_CALC_LAST_RESULT
    [[ -n $r && $BUFFER == $_CALC_LAST_BUFFER ]] || { _calc_qalc_eval "$_CALC_QEXPR"; r=$_CALC_QRESULT; }
    print -s -- "$BUFFER"                          # history keeps what was typed
    [[ -n $r ]] && _CALC_PENDING="$_CALC_QEXPR = $r"
    BUFFER=
  elif [[ -n $_CALC_LAST_RESULT && $BUFFER == $_CALC_LAST_BUFFER ]] \
     && _calc_is_expr "$BUFFER"; then
    print -s -- "$BUFFER"                          # history keeps the expression
    _CALC_PENDING="$BUFFER = $_CALC_LAST_RESULT"    # _calc_flush prints it
    BUFFER=                                         # nothing runs
  fi
  # Clear our preview and reset state so nothing leaks into the next prompt.
  _calc_clear
  _CALC_LAST_BUFFER=$'\0'
  _CALC_LAST_RESULT=
  zle .accept-line
}

# Bind the live preview to the redraw hook and intercept Enter.
#
# zle-line-pre-redraw is unused in this setup, so we own it directly with
# "zle -N", which (unlike add-zle-hook-widget) takes effect at .zshrc source
# time. If you later add a plugin that also drives line-pre-redraw
# (zsh-autosuggestions, zsh-syntax-highlighting), switch to add-zle-hook-widget
# registered from a one-shot precmd so the hooks chain instead of clobbering.
autoload -Uz add-zsh-hook
add-zsh-hook precmd _calc_flush
add-zsh-hook zshexit _calc_qco_stop      # kill the qalc coprocess on shell exit
zle -N zle-line-pre-redraw _calc_preview
zle -N accept-line         _calc_accept_line
