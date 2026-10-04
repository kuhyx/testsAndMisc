#!/bin/bash

# ============================================================================
# ci_mirror_async.sh — run the CI mirror off the push's critical path.
#
# Sourced by ci_mirror.sh; not executable on its own. Paths are computed in
# functions, not at source time: this file is sourced before ci_mirror.sh
# defines VENV_DIR.
#
# The mirror is real verification: a clean venv, pre-commit over the push
# range (or every file when the gate's own config changed) and pytest. That
# is ~22s for an ordinary push, ~70s when requirements.txt moves, minutes for
# a full sweep. None of it caches down to a second, because it is work rather
# than overhead.
#
# So it stops blocking the push. `git push` spawns a detached, niced worker
# and returns; the worker records a verdict for the tree it checked. The
# guarantee is kept one push later: a recorded failure refuses the next push
# until the tree is verified in the foreground, so a broken tree reaches
# GitHub at most once — where CI sees the same commit within minutes anyway.
#
# Escape hatch:  CI_MIRROR_SYNC=1 git push   verify now, in the foreground.
# ============================================================================

verdict_dir() { printf '%s/verdicts' "$VENV_DIR"; }
last_verdict_file() { printf '%s/last' "$(verdict_dir)"; }
worker_lock() { printf '%s/.worker.lock' "$VENV_DIR"; }
green_cache() { printf '%s/.last-green-tree' "$VENV_DIR"; }
head_tree() { git -C "$ROOT" rev-parse 'HEAD^{tree}'; }

# A tree that already passed the full gate needs nothing redone.
tree_is_known_green() {
	local stored
	[[ -f "$(green_cache)" ]] || return 1
	stored="$(cat "$(green_cache)")"
	[[ "$(head_tree)" == "$stored" ]]
}

record_tree_green() {
	head_tree >"$(green_cache)" 2>/dev/null || true
}

# A verdict is "<state> <tree> <logfile>"; only completed runs write one.
record_verdict() {
	mkdir -p "$(verdict_dir)"
	printf '%s %s %s\n' "$1" "$2" "$3" >"$(last_verdict_file)"
}

# Fail closed one push late.
block_on_previous_failure() {
	local file state tree logfile
	file="$(last_verdict_file)"
	[[ -f "$file" ]] || return 0
	read -r state tree logfile <"$file"
	[[ "$state" == "fail" ]] || return 0
	log "the previous background mirror FAILED (tree ${tree:0:12})"
	if [[ -f "$logfile" ]]; then
		tail -n 40 "$logfile" >&2
	fi
	log "refusing to push on top of a failed verification"
	log "re-verify in the foreground with:  CI_MIRROR_SYNC=1 git push"
	exit 1
}

# The worker inherits the push range, so it checks exactly what the push did.
spawn_worker() {
	local tree logfile
	tree="$(head_tree)"
	logfile="$(verdict_dir)/${tree}.log"
	mkdir -p "$(verdict_dir)"

	# Always spawn: run_as_worker takes the lock and blocks, so workers
	# serialise rather than compete, and every pushed tree gets its own
	# verdict. Skipping the spawn while another run was in flight would
	# leave the newer tree unverified for good.
	setsid nice -n 19 ionice -c 3 env \
		CI_MIRROR_WORKER=1 \
		CI_MIRROR_TREE="$tree" \
		CI_MIRROR_LOG="$logfile" \
		PRE_COMMIT_FROM_REF="${PRE_COMMIT_FROM_REF:-}" \
		PRE_COMMIT_TO_REF="${PRE_COMMIT_TO_REF:-}" \
		bash "$ROOT/meta/scripts/ci_mirror.sh" >/dev/null 2>&1 </dev/null &
	disown

	log "verification running in the background (tree ${tree:0:12})"
	log "log: $logfile — a failure blocks the next push"
}

# The detached worker: same gates, but its exit state becomes the verdict
# rather than the push's.
run_as_worker() {
	local tree logfile
	tree="${CI_MIRROR_TREE:-$(head_tree)}"
	logfile="${CI_MIRROR_LOG:-$(verdict_dir)/${tree}.log}"
	mkdir -p "$(verdict_dir)"
	(
		flock 9
		if run_full_gate >"$logfile" 2>&1; then
			record_verdict ok "$tree" "$logfile"
		else
			record_verdict fail "$tree" "$logfile"
		fi
	) 9>"$(worker_lock)"
}
