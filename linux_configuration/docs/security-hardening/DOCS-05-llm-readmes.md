## Part 5: LLM README Files

These should be created in the respective directories:

### [hosts/guard/README_FOR_LLM.md](to be created)

```markdown
# Hosts Guard System - LLM Reference

## Purpose

Prevent tampering with /etc/hosts to maintain website blocking.

## Architecture
```

/etc/hosts (immutable) ←── canonical (/usr/local/share/locked-hosts)
↑
path watcher detects changes
↓
enforce-hosts.sh restores

````

## Critical Files
| File | Purpose | Protected By |
|------|---------|--------------|
| /etc/hosts | Actual hosts file | chattr +i, bind mount |
| /usr/local/share/locked-hosts | Canonical copy | chattr +i |
| /etc/hosts.custom-entries.state | Tracks blocked domains | chattr +i |

## Commands to Know
```bash
# Check protection status
lsattr /etc/hosts
systemctl status hosts-guard.path hosts-bind-mount.service

# Legitimate edit (with delay)
sudo /usr/local/sbin/unlock-hosts

# Reinstall/repair
sudo ~/src/hosts-blocker/install.sh
sudo ~/src/hosts-blocker/guard/setup_hosts_guard.sh
````

## DO NOT

- Edit /etc/nsswitch.conf (bypasses hosts entirely)
- Stop hosts-guard.path without understanding consequences
- Remove entries from install.sh without state file cleanup

````

### [periodic_background/digital_wellbeing/pacman/README_FOR_LLM.md](to be created)

```markdown
# Pacman Wrapper - LLM Reference

## Purpose
Intercept pacman to enforce package installation policies.

## Architecture
````

/usr/bin/pacman (symlink) → pacman_wrapper.sh
↓
/usr/bin/pacman.orig (real)

````

## Files
| File | Purpose |
|------|---------|
| words.txt | Word scramble challenge source |

_Package policy lists (blocked keywords, whitelist, greylist) were retired 2026-10-17; hosts/DNS blocking covers them._

## Hardcoded Checks (cannot bypass via files)
- VirtualBox → security challenge + hosts enforcement
- Steam → weekend-only + word scramble

## Integration Points
1. Hosts guard (pre/post hooks)
2. Periodic maintenance (auto-setup if missing)
3. VirtualBox hosts enforcement

## Updating the wrapper
```bash
# Re-run installer to update checksums
sudo ./install_pacman_wrapper.sh
````

```

```
