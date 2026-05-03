# Shell Script Quality & Efficiency Guidelines

## Overview

This repository uses **three layers of shell script quality control**:

1. **shellcheck** - Syntax and common errors (pre-commit)
2. **polling antipatterns detector** - Fork-storm prevention (pre-commit, NEW)
3. **shell.instructions** - Best practices (in-editor, via Copilot)

## What Changed

### New: Polling Antipatterns Pre-commit Hook

**File**: `scripts/check_polling_antipatterns.sh`  
**Hook ID**: `no-polling-antipatterns`  
**When**: Automatically runs on `.sh` files during `pre-commit run` or `git commit`

The hook detects and **blocks commits** of shell scripts with these anti-patterns:

| Anti-pattern                            | Why bad            | Detector             |
| --------------------------------------- | ------------------ | -------------------- |
| `while true; do [check]; sleep 1; done` | 60k forks/hour     | Loop + sleep pattern |
| `$(date +...)` in monitoring            | 10ms fork per call | Subprocess date      |
| `pgrep/xdotool` in polling              | 5ms fork per call  | Process inspection   |
| `\| awk \| grep \| tr` chains           | Fork per pipe      | Heavy piping         |
| `sleep 0.5` aggressive                  | Fork storm         | Sub-second polling   |

### Updated: Shell Instructions

**File**: `/home/kuhy/.copilot/instructions/shell.instructions.md`  
**New section**: "⚡ Efficient Polling & Monitoring Scripts"

Explains the **R1-R8 rules** for writing zero-fork polling scripts:

- R1: Zero forks in hot path
- R2: Use /proc and /sys directly
- R3: Event-driven over polling
- R4: i3blocks `interval=persist`
- R5: Increase polling intervals
- R6: Cache expensive values
- R7: Profile before deployment
- R8: Recognize fork-storm signatures

## Usage

### For Developers

#### 1. Write compliant polling scripts

Follow the patterns in `.copilot/instructions/shell.instructions.md`:

```bash
#!/bin/bash
# ✅ Zero-fork polling script example

set -u

emit() {
  printf '  %s\n' "$1"
}

# Read from /proc directly (no fork)
read -r uptime_s _ < /proc/uptime
current_time=${uptime_s%%.*}

# Event-driven if possible, else increase interval
emit "Time: $current_time"
```

#### 2. Pre-commit runs automatically

```bash
# Commits that violate anti-patterns are blocked:
git commit -m "Add new polling script"
# ❌ BLOCKED if script violates rules

# Fix the script:
# - Replace $(date) with /proc reads
# - Replace while true + sleep with event-driven I/O
# - Remove aggressive sleep intervals
# - Reduce piped commands

git commit -m "Add new polling script"
# ✅ PASSES

# Or run manually:
pre-commit run no-polling-antipatterns --files my_script.sh
```

#### 3. Use diagnostic tools

```bash
cd /home/kuhy/testsAndMisc

# Find all polling anti-patterns in repo
./run.sh --diagnose

# Profile for 30s to find active fork storms
./run.sh --profile 30

# Generate resource report
./run.sh
```

### For Code Reviewers

When reviewing shell scripts:

1. **Check if hook ran**: Pre-commit output should show `no-polling-antipatterns` passed
2. **Look for**:
   - `while true` + `sleep` → suggest event-driven
   - `$(date ...)` → suggest `/proc/uptime`
   - Multiple pipes → suggest bash builtins
   - `pgrep` in loops → suggest caching
3. **Reference**: Point to shell.instructions section "⚡ Efficient Polling & Monitoring Scripts"

## Examples

### Example 1: Polling Loop ❌ → ✅

```bash
# ❌ FAILS pre-commit check
#!/bin/bash
while true; do
  now=$(date +%s)
  echo "Current: $now"
  sleep 1
done

# ✅ PASSES - uses /proc/uptime, adaptive sleep
#!/bin/bash
emit() { printf '  %s\n' "$1"; }

emit "$(initial_value)"
while true; do
  read -r uptime_s _ < /proc/uptime
  emit "Current: ${uptime_s%%.*}"

  if is_active; then
    sleep 0.5
  else
    sleep 3  # Adaptive polling
  fi
done
```

### Example 2: i3blocks Status Script ❌ → ✅

```bash
# ❌ INEFFICIENT - forked every 5 seconds
#!/bin/bash
# battery.sh
cap=$(cat /sys/class/power_supply/BAT0/capacity)
echo "  $cap%"

# i3blocks config:
# [battery]
# interval=5
# Result: 720 checks/hour × 1 fork = 720 forks/hour

# ✅ OPTIMIZED - zero fork when idle
#!/bin/bash
# battery.sh
set -u
emit() { printf '  %s%%\n' "$1"; }

read -r cap < /sys/class/power_supply/BAT0/capacity
emit "$cap"

# Watch for power supply changes (blocks when idle)
udevadm monitor --udev --property --subsystem-match=power_supply |
while IFS='=' read -r key value || true; do
  [[ $key == POWER_SUPPLY_CAPACITY ]] || continue
  read -r cap < /sys/class/power_supply/BAT0/capacity
  emit "$cap"
done

# i3blocks config:
# [battery]
# interval=persist
# Result: Zero CPU when plugged in, one fork per cable plug/unplug
```

### Example 3: Process Monitoring ❌ → ✅

```bash
# ❌ FAILS - pgrep in loop = fork per second × N processes
while true; do
  if pgrep -f "python" > /dev/null; then
    echo "Python running"
  fi
  sleep 1
done

# ✅ PASSES - adaptive polling with cached check
focus_running=0
while true; do
  if is_focus_app_running; then
    focus_running=1
  else
    if ((focus_running)); then
      echo "Focus ended"
      focus_running=0
    fi
  fi

  if ((focus_running)); then
    sleep 0.5  # Active
  else
    sleep 3    # Idle
  fi
done
```

## Integration with Existing Tools

### With shellcheck

Pre-commit runs both:

```bash
pre-commit run shellcheck --files my_script.sh
pre-commit run no-polling-antipatterns --files my_script.sh
```

### With formatting

Polling linter runs alongside code formatters:

```bash
pre-commit run --all-files
# → trailing-whitespace, shellcheck, no-polling-antipatterns, ruff, etc.
```

### With CI/CD

Pre-commit hooks are required before:

- `git commit` (pre-commit hook)
- `git push` (pre-push hook, includes slower tests)

Scripts that fail the polling detector must be fixed before pushing.

## Exemptions

Some scripts are exempted (e.g., C/CPP test utilities):

```yaml
# .pre-commit-config.yaml
- id: no-polling-antipatterns
  exclude: ^(\.git/|C/|CPP/|phone_focus_mode/lib/tests/)
```

To add an exemption, modify `.pre-commit-config.yaml` and explain why in a comment.

## Common Questions

**Q: My status-bar script is trivial—do I need to optimize it?**  
A: Yes! A 100-byte script that forks once per second still costs ~30 CPU-seconds per day. Use `/proc` reads instead.

**Q: Can I suppress the antipatterns check?**  
A: No, by design. (See `.git/hooks/` and `userMemory: lint-rules.md` for why). Instead, fix the underlying issue—it's usually a 2-line change.

**Q: What if my script MUST call `date`?**  
A: Use bash builtin: `printf -v now '%(%Y-%m-%d)T' -1` (no fork).

**Q: Why block on every commit?**  
A: Polling fork-storms cause system-wide slowdown. This saves hundreds of CPU-hours per year per developer machine.

## Resources

- **Shell Instructions**: `.copilot/instructions/shell.instructions.md` (in-editor, Copilot knowledge)
- **Efficiency Skill**: `.github/skills/efficient-polling-scripts/SKILL.md` (detailed patterns)
- **Live Tools**:
  - `./run.sh --diagnose` - Audit repo for patterns
  - `./run.sh --profile 30` - Profile live system
  - `scripts/check_polling_antipatterns.sh` - Manual check

## Summary

| Layer                 | Tool                          | Purpose                                      |
| --------------------- | ----------------------------- | -------------------------------------------- |
| **1. Syntax**         | shellcheck                    | Catch bugs, unused variables, quoting issues |
| **2. Efficiency**     | check_polling_antipatterns.sh | Block fork-storm patterns                    |
| **3. Best Practices** | shell.instructions.md         | Guide developers toward optimal patterns     |

All three work together to ensure shell scripts are **safe, efficient, and maintainable**.
