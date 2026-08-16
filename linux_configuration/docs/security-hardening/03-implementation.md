## Part 3: Implementation Prompt

**Use this prompt in a new conversation to implement the changes:**

---

### IMPLEMENTATION PROMPT

````
I need to implement comprehensive security hardening for a Linux digital wellbeing system.
The codebase is at ~/linux-configuration/ with these components needing changes:

## 1. HOSTS PROTECTION - nsswitch.conf Guard

Location: hosts/guard/

Create a new protection layer for /etc/nsswitch.conf that:
- Monitors nsswitch.conf for changes (systemd path watcher)
- Ensures the "hosts:" line ALWAYS contains "files" before "dns"
- Creates canonical copy at /usr/local/share/locked-nsswitch.conf
- Enforces with chattr +i
- Add to setup_hosts_guard.sh installer
- Must restore automatically if tampered

The nsswitch.conf protection is CRITICAL because removing "files" from the
hosts line completely bypasses /etc/hosts without touching it.

## 2. MIDNIGHT SHUTDOWN - Silent Denial

Location: scripts/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh

Changes needed:
- Remove ALL helpful messages about how to bypass (unlock-shutdown-schedule path)
- When user tries to make schedule more lenient:
  - Simply say "Operation not permitted" with NO explanation
  - Do NOT mention the unlock script
  - Do NOT explain what's being blocked
  - Silently restore canonical values
- The unlock script should still exist but be undiscoverable
- Consider renaming unlock script to an obscure name
- Remove the unlock script path from any logs

## 3. SCREEN LOCKER - External Repo

Location: ~/testsAndMisc/python_pkg/screen_locker/screen_lock.py

Changes needed:
- REMOVE the "Running" workout option entirely (too easy to fake)
- For "Table Tennis":
  - Require minimum 15 sets played
  - Add verification: total_points = points_won + points_lost
  - Require that total_points >= sets_played * 11 (minimum points per set)
  - Add random math verification question about the scores
  - Increase submit delay to 60 seconds
- For "Strength":
  - Already has good verification, keep as-is
- Add input focus grabbing to prevent Alt+Tab escape
- Disable window close keyboard shortcuts

## 4. PACMAN WRAPPER - Chrome Block + LeechBlock Auto-Install

Location: scripts/periodic_background/digital_wellbeing/pacman/

Changes needed to pacman_blocked_keywords.txt:
- Add: google-chrome
- Add: google-chrome-stable
- Add: chromium
- Add: ungoogled-chromium

New behavior in pacman_wrapper.sh:
- After ANY browser is detected installed (via pacman -Qq check):
  - Automatically run install_leechblock.sh if it exists
  - LeechBlock installer should:
    - Detect browser type
    - Install extension with pre-configured blocking rules
    - Use firefox-addon-install method or chrome native messaging
- If LeechBlock installation fails, BLOCK the browser binary (wrap it)

## 5. BLOCK COMPULSIVE OPENING - Auto-Close Timer

Location: scripts/periodic_background/digital_wellbeing/block_compulsive_opening.sh

New behavior:
- After app is allowed to open, start a background timer
- After 10 minutes, forcefully close the app (pkill)
- Show warning notification at 8 minutes ("Closing in 2 minutes")
- The wrapper should spawn a detached monitoring process
- State tracking: record PID and launch time
- Check for zombie PIDs and clean up state

Implementation approach:
```bash
# After exec line in wrapper_main, instead of direct exec:
launch_with_timer() {
  local app="$1"
  local timeout_minutes=10
  local real_binary="$2"
  shift 2

  # Launch app in background
  "$real_binary" "$@" &
  local app_pid=$!

  # Record state
  echo "$app_pid $(date +%s)" > "$STATE_DIR/${app}.running"

  # Spawn killer daemon (detached)
  (
    sleep $((timeout_minutes * 60))
    if kill -0 $app_pid 2>/dev/null; then
      notify "$app" "Session timeout - closing now" critical
      kill $app_pid 2>/dev/null
      sleep 2
      kill -9 $app_pid 2>/dev/null || true
    fi
    rm -f "$STATE_DIR/${app}.running"
  ) &
  disown

  # Wait for app to exit
  wait $app_pid 2>/dev/null || true
}
````

## 6. YOUTUBE MUSIC → STEAM/BROWSER MUTUAL EXCLUSION

This requires a more sophisticated approach. Create a new Python daemon.

Location: scripts/periodic_background/digital_wellbeing/focus_mode_daemon.py (new file)

Behavior:

- Run as a systemd user service
- Monitor running processes continuously
- When Steam (steam*app*\* or steam game processes) detected:
  - Kill any running browsers (firefox, chrome, brave, etc.)
  - Block browser launches (via wrapper modification or DBus signal)
  - Show notification: "Gaming mode active - browsers disabled"
- When any browser detected:
  - Kill Steam processes
  - Block Steam launches
  - Show notification: "Browsing mode active - Steam disabled"
- Mutual exclusion: whichever started first "wins"
- The youtube-music-wrapper.sh should also check for this daemon's signals

## ADDITIONAL REQUIREMENTS

1. All changes must be idempotent (can re-run safely)
2. All protection mechanisms should fail-closed (if service dies, restrictions remain)
3. Log all tampering attempts to /var/log/digital-wellbeing-guard.log
4. Create a single test script that verifies all protections work
5. Update the .github/copilot-instructions.md with the new components

## FILES TO CREATE/MODIFY

New files:

- hosts/guard/nsswitch-guard.path
- hosts/guard/nsswitch-guard.service
- hosts/guard/enforce-nsswitch.sh
- scripts/periodic_background/digital_wellbeing/focus_mode_daemon.py
- scripts/periodic_background/digital_wellbeing/install_focus_mode_daemon.sh
- tests/test_security_hardening.sh

Modified files:

- hosts/guard/setup_hosts_guard.sh (add nsswitch protection)
- scripts/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh (remove helpful messages)
- scripts/periodic_background/digital_wellbeing/pacman/pacman_blocked_keywords.txt (add chrome)
- scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh (leechblock auto-install)
- scripts/periodic_background/digital_wellbeing/block_compulsive_opening.sh (auto-close timer)
- scripts/periodic_background/digital_wellbeing/youtube-music-wrapper.sh (daemon integration)

External repo (separate changes):

- ~/testsAndMisc/python_pkg/screen_locker/screen_lock.py (remove running, harden table tennis)

```

```
