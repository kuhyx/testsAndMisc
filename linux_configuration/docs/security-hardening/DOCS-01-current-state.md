## Part 1: Current State Analysis

### 1. `/etc/hosts` Protection System

**Files involved:**

- [hosts/install.sh](../hosts/install.sh) - Main hosts installer
- [hosts/guard/setup_hosts_guard.sh](../hosts/guard/setup_hosts_guard.sh) - Guard layer setup
- [hosts/guard/enforce-hosts.sh](../hosts/guard/enforce-hosts.sh) - Enforcement script
- [hosts/guard/psychological/unlock-hosts.sh](../hosts/guard/psychological/unlock-hosts.sh) - Delayed unlock

**Current Protection Layers:**

1. ✅ Immutable attribute (`chattr +i`)
2. ✅ Canonical copy at `/usr/local/share/locked-hosts`
3. ✅ Path watcher (`hosts-guard.path`) auto-restores on modification
4. ✅ Read-only bind mount (`hosts-bind-mount.service`)
5. ✅ Custom entries protection (blocks removal of blocked domains)
6. ✅ Shell history suppression for `unlock-hosts` command

**CRITICAL VULNERABILITY IDENTIFIED:**

- ❌ **NO protection for `/etc/nsswitch.conf`** - A user can simply edit nsswitch.conf and remove `files` from the `hosts:` line, completely bypassing ALL /etc/hosts protections without touching the hosts file itself!

**Example bypass:**

```bash
# Original: hosts: mymachines resolve [!UNAVAIL=return] files myhostname dns
# Tampered: hosts: mymachines resolve [!UNAVAIL=return] myhostname dns
# Result: /etc/hosts is completely ignored by the system
```

---

### 2. Midnight Shutdown System

**Files involved:**

- [periodic_background/digital_wellbeing/setup_midnight_shutdown.sh](../periodic_background/digital_wellbeing/setup_midnight_shutdown.sh) (1359 lines)

**Current Protection Layers:**

1. ✅ Immutable attribute on `/etc/shutdown-schedule.conf`
2. ✅ Canonical copy at `/usr/local/share/locked-shutdown-schedule.conf`
3. ✅ Path watcher restores config if tampered
4. ✅ Schedule protection blocks making schedule more lenient
5. ✅ Unlock script with psychological delay

**VULNERABILITIES IDENTIFIED:**

- ❌ The unlock script **explicitly tells users how to bypass**: "sudo /usr/local/sbin/unlock-shutdown-schedule"
- ❌ The schedule change logic is communicated in the error message
- ❌ No protection against stopping/disabling the timer services
- ❌ No protection against modifying the check script at `/usr/local/bin/day-specific-shutdown-check.sh`

---

### 3. Screen Locker (Python - External Repo)

**File:** `/home/kuhy/testsAndMisc/python_pkg/screen_locker/screen_lock.py`

**Current Workout Types:**

1. Running - distance, time, pace validation
2. Strength - exercises, sets, reps, weights, total calculation
3. Table Tennis - duration, sets, points won/lost

**VULNERABILITIES IDENTIFIED:**

- ❌ **Running option too easy to fake** - just enter plausible numbers
- ❌ **Table Tennis lacks real verification** - no mathematical cross-check
- ❌ Users can close the window via keyboard shortcuts (Alt+F4, etc.)
- ❌ The unlock mechanism is too simple once you know the forms
- ❌ Shutdown time adjustment is a REWARD for working out (can be exploited)

---

### 4. Pacman Wrapper

**Files involved:**

- [periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh](../periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh) (823 lines)
- [periodic_background/digital_wellbeing/pacman/pacman_blocked_keywords.txt](../periodic_background/digital_wellbeing/pacman/pacman_blocked_keywords.txt)
- [periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh](../periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh)

**Current Protection:**

1. ✅ Policy file integrity verification (SHA256)
2. ✅ Blocked keywords list
3. ✅ Greylist with challenge
4. ✅ VirtualBox hardcoded check (cannot bypass via policy files)
5. ✅ Steam weekend-only restriction

**VULNERABILITIES IDENTIFIED:**

- ❌ **Google Chrome not blocked** - `google-chrome` and `google-chrome-stable` missing from blocked list
- ❌ No automatic LeechBlock installation when browsers are detected
- ❌ User can download `.deb`/`.tar.gz` and install manually

---

### 5. Block Compulsive Opening

**File:** [periodic_background/digital_wellbeing/block_compulsive_opening.sh](../periodic_background/digital_wellbeing/block_compulsive_opening.sh) (507 lines)

**Current Behavior:**

- Records first open per hour in state file
- Blocks subsequent launches within same hour
- Shows notification when blocked

**CRITICAL VULNERABILITY:**

- ❌ **App stays running indefinitely** - User can:
  1. Open app once per hour (allowed)
  2. Minimize/hide the window
  3. Keep it running forever in background
  4. Compulsive checking still happens, just via Alt+Tab instead of launcher

---

### 6. YouTube Music Wrapper

**File:** [periodic_background/digital_wellbeing/youtube-music-wrapper.sh](../periodic_background/digital_wellbeing/youtube-music-wrapper.sh)

**Current Behavior:**

- Checks if focus apps (VSCode, games, etc.) are running
- Blocks YouTube Music launch if focus app detected

**REQUESTED ENHANCEMENT:**

- When Steam is open → Block ALL browsers, close any open browsers
- When browsers open → Block Steam, close Steam if running
- This creates mutual exclusion between gaming and browsing
