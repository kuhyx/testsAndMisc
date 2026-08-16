# calc-live-qalc.zsh — the warmed qalc coprocess for "="-prefixed lines
# ----------------------------------------------------------------------------
# Sourced by calc-live.zsh; split out to keep both files under the 250-line
# cap. Not standalone: it relies on _CALC_QALC_BIN and _CALC_TIMEOUT_BIN, which
# calc-live.zsh sets above the source line.

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
