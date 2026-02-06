# AI agent quickstart for this repo

This repo automates Linux desktop bootstrap, hardening, and i3 setup. It’s primarily Bash scripts with idempotent installers, systemd units, and policy guardrails. Use these notes to work effectively with the codebase.

## Big picture
- fresh-install/: end-to-end bootstrap for Arch/Ubuntu workstations. Reads package lists, configures pacman/makepkg, sets up GPU drivers, i3, hosts guard, pacman wrapper, and useful services. Example: `fresh-install/main.sh` orchestrates most steps and sources `detect_gpu*.sh`.
- hosts/: manages a highly-opinionated `/etc/hosts` via StevenBlack upstream with custom edits, plus “guard” friction:
  - `hosts/install.sh` builds and locks `/etc/hosts` (immutable/append-only; selective unblocks; custom blocks).
  - `hosts/guard/` installs enforcement: `enforce-hosts.sh`, path-watcher `hosts-guard.path` -> `hosts-guard.service`, optional RO bind mount, pacman hooks, and a delayed editor `psychological/unlock-hosts.sh`.
- scripts/digital_wellbeing/pacman/: a policy-aware pacman wrapper with friction mechanics.
  - `pacman_wrapper.sh` intercepts transactions, runs hosts-guard pre/post hooks, handles stale db lock, auto-wires maintenance services, and enforces package policy (blocked/whitelisted lists); adds weekend-only “Steam” challenge and a VirtualBox challenge powered by `words.txt`.
  - `install_pacman_wrapper.sh` backs up `/usr/bin/pacman` to `pacman.orig` and symlinks to the wrapper.
- scripts/system-maintenance/: templates and installer for periodic jobs and monitoring.
  - `setup_periodic_system.sh` installs: `/usr/local/bin/periodic-system-maintenance.sh`, a timer (`periodic-system-maintenance.timer`), a startup oneshot, and `hosts-file-monitor.service` that restores `/etc/hosts` if tampered. Also installs a browser pre-exec wrapper that re-runs the hosts installer before launching common browsers.
- i3-configuration/: installs i3 and i3blocks configs with small font sizing logic (`i3-configuration/install.sh`).

## Conventions you should follow
- Bash style: use `set -e` or `set -euo pipefail`, re-exec with sudo if not root, be idempotent, and log to `/var/log/*` with timestamps. Examples: `setup_periodic_system.sh`, `hosts/guard/setup_hosts_guard.sh`.
- Install via templates: scripts under `scripts/system-maintenance/bin` and `.../systemd` are templates. The setup script substitutes placeholders like `__HOSTS_INSTALL_SCRIPT__` and `__PACMAN_WRAPPER_INSTALL__` before installing to `/usr/local/bin` and `/etc/systemd/system`. Don’t edit installed copies directly; modify templates and the setup script.
- Package lists: `fresh-install/pacman_packages.txt` and `aur_packages.txt` treat any line not starting with lowercase alnum as a comment.

## Core workflows (what to run)
- Fresh machine: run from repo root
  - `fresh-install/main.sh` (bootstraps configs, GPU, hosts, i3, pacman wrapper, services). It assumes the repo is at `~/linux-configuration` in some steps.
- Periodic services: `sudo scripts/setup_periodic_system.sh` (installs timer, startup service, hosts monitor, and browser pre-exec wrapper; then performs an initial run).
- Pacman wrapper only: `sudo scripts/digital_wellbeing/pacman/install_pacman_wrapper.sh` (backs up pacman and wires the wrapper). The wrapper auto-runs hosts-guard pre/post hooks and can self-setup periodic services when missing.
- Hosts guard:
  - `sudo hosts/install.sh` to (re)build `/etc/hosts` from cache/upstream then lock it.
  - `sudo hosts/guard/setup_hosts_guard.sh` to install guard layers; then `hosts/guard/install_pacman_hooks.sh` to add pacman pre/post unlock hooks.
  - To edit `/etc/hosts`: run `/usr/local/sbin/unlock-hosts` (delays, opens editor, re-applies protections).
- i3 config: `i3-configuration/install.sh` (copies `i3` and `i3blocks`, adjusts font size; installs required tools conditionally for Arch/Ubuntu).

## Integration points and gotchas
- Pacman interception: `pacman_wrapper.sh` sets `PACMAN_BIN=/usr/bin/pacman.orig` and symlinks `/usr/bin/pacman` -> wrapper. Keep this invariant when changing the wrapper.
- Hosts hooks: Wrapper calls `/usr/local/share/hosts-guard/pacman-pre-unlock-hosts.sh` and `...post-relock-hosts.sh` if installed; keep paths stable or update both installer and wrapper.
- Logs: check `/var/log/periodic-system-maintenance.log` and `/var/log/hosts-file-monitor.log` for service behavior; timer and services live under `scripts/system-maintenance/systemd/` (templates).
- Browser pre-exec: setup creates `/usr/local/bin/browser-preexec-wrapper` and symlinks common browser names to it; it silently re-runs the hosts installer before launching the real binary in `/usr/bin`.

## Patterns to reuse when adding features
- Follow the sudo re-exec + idempotent install pattern from `setup_periodic_system.sh` and `hosts/guard/setup_hosts_guard.sh`.
- Add new periodic behaviors as templates under `scripts/system-maintenance/bin` and `.../systemd`, then extend `setup_periodic_system.sh` to install/enable them.
- Extend package policy by updating `scripts/digital_wellbeing/pacman/pacman_blocked_keywords.txt` or by adding `check_for_<pkg>` + `prompt_for_<pkg>_challenge` blocks in the wrapper.
- Run `scripts/meta/shell_check.sh` to detect things to fix before committing.
## Detailed LLM Documentation

For in-depth understanding of specific components, see these dedicated guides:

- **Hosts Guard**: [hosts/guard/README_FOR_LLM.md](../hosts/guard/README_FOR_LLM.md) - Protection layers, canonical copies, path watchers
- **Pacman Wrapper**: [scripts/digital_wellbeing/pacman/README_FOR_LLM.md](../scripts/digital_wellbeing/pacman/README_FOR_LLM.md) - Policy files, integrity checks, challenges
- **Midnight Shutdown**: [scripts/digital_wellbeing/README_MIDNIGHT_SHUTDOWN_LLM.md](../scripts/digital_wellbeing/README_MIDNIGHT_SHUTDOWN_LLM.md) - Schedule protection, timer system
- **Compulsive Block**: [scripts/digital_wellbeing/README_COMPULSIVE_BLOCK_LLM.md](../scripts/digital_wellbeing/README_COMPULSIVE_BLOCK_LLM.md) - App launch limiting
- **Security Analysis**: [docs/SECURITY_HARDENING_ANALYSIS.md](../docs/SECURITY_HARDENING_ANALYSIS.md) - Vulnerabilities and implementation roadmap

## Digital Wellbeing Components Summary

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| Hosts Guard | Block websites via /etc/hosts | `hosts/install.sh`, `hosts/guard/*` |
| Pacman Wrapper | Block package installation | `scripts/digital_wellbeing/pacman/*` |
| Midnight Shutdown | Auto-shutdown at night | `scripts/digital_wellbeing/setup_midnight_shutdown.sh` |
| Compulsive Block | Limit app launches | `scripts/digital_wellbeing/block_compulsive_opening.sh` |
| Music Wrapper | Block music during focus | `scripts/digital_wellbeing/youtube-music-wrapper.sh` |
| Screen Locker | Require workout to unlock | External: `~/testsAndMisc/python_pkg/screen_locker/` |