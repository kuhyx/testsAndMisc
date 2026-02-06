#!/bin/bash
# Script to check and enable all digital wellbeing services
# Checks: pacman wrapper, midnight shutdown, startup monitor, periodic systems, hosts and hosts guard
#
# Usage:
#   sudo ./check_and_enable_services.sh [options]
# Options:
#   --dry-run    Show what would be done without making changes
#   --status     Only show status, don't enable anything
#   -h|--help    Show help

set -euo pipefail

######################################################################
# Configuration
######################################################################
DRY_RUN=0
STATUS_ONLY=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script and config directories
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
CONFIG_DIR="$(dirname "$SCRIPT_DIR")"

# Script paths
PACMAN_WRAPPER_INSTALL="$CONFIG_DIR/scripts/digital_wellbeing/pacman/install_pacman_wrapper.sh"
MIDNIGHT_SHUTDOWN_SCRIPT="$CONFIG_DIR/scripts/digital_wellbeing/setup_midnight_shutdown.sh"
STARTUP_MONITOR_SCRIPT="$CONFIG_DIR/scripts/digital_wellbeing/setup_pc_startup_monitor.sh"
PERIODIC_SYSTEM_SCRIPT="$CONFIG_DIR/scripts/setup_periodic_system.sh"
HOSTS_INSTALL_SCRIPT="$CONFIG_DIR/hosts/install.sh"
HOSTS_GUARD_SCRIPT="$CONFIG_DIR/hosts/guard/setup_hosts_guard.sh"
HOSTS_PACMAN_HOOKS_SCRIPT="$CONFIG_DIR/hosts/guard/install_pacman_hooks.sh"

######################################################################
# Helpers
######################################################################
msg() { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
note() { printf "${BLUE}[i]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err() { printf "${RED}[✗]${NC} %s\n" "$*"; }
header() { printf "\n${CYAN}=== %s ===${NC}\n" "$*"; }

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo -e "${YELLOW}DRY-RUN:${NC} $*"
    return 0
  else
    "$@"
  fi
}

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "This script requires root privileges."
    echo "Re-executing with sudo..."
    exec sudo -E bash "$0" "$@"
  fi
}

usage() {
  cat << 'EOF'
Check and Enable Digital Wellbeing Services
============================================

Usage: sudo ./check_and_enable_services.sh [options]

Options:
  --dry-run    Show what would be done without making changes
  --status     Only show status, don't enable anything
  -h, --help   Show this help message

Services checked:
  1. Pacman wrapper - Policy-aware pacman wrapper with friction mechanics
  2. Midnight shutdown - Day-specific automatic shutdown timer
  3. Startup monitor - PC startup time monitoring service
  4. Periodic systems - Hourly maintenance timer and hosts monitor
  5. Hosts and guards - /etc/hosts blocking and protection layers
EOF
}

######################################################################
# Parse arguments
######################################################################
ORIGINAL_ARGS=("$@")
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --status)
      STATUS_ONLY=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      err "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

require_root "${ORIGINAL_ARGS[@]}"

######################################################################
# Status tracking
######################################################################
declare -A SERVICE_STATUS
ISSUES_FOUND=0
FIXES_APPLIED=0

######################################################################
# Report issues and optionally run fix script
# Usage: report_and_fix issues_array status_var status_key fix_note setup_script verify_service [args...]
######################################################################
report_and_fix() {
  local -n _issues=$1
  local -n _status=$2
  local status_key="$3"
  local fix_note="$4"
  local setup_script="$5"
  local verify_service="${6:-}"
  shift 6
  local script_args=("$@")

  if [[ $_status != "ok" ]]; then
    for issue in "${_issues[@]}"; do
      if [[ $_status == "error" ]]; then
        err "$issue"
      else
        warn "$issue"
      fi
    done
    ((ISSUES_FOUND++)) || true

    if [[ $STATUS_ONLY -eq 0 && $_status == "error" ]]; then
      note "$fix_note"
      if [[ -f $setup_script ]]; then
        run bash "$setup_script" "${script_args[@]}"
        ((FIXES_APPLIED++)) || true
        # Re-verify after fix
        if [[ $DRY_RUN -eq 0 && -n $verify_service ]] && systemctl is-enabled "$verify_service" &> /dev/null; then
          _status="ok"
        fi
      else
        err "Setup script not found: $setup_script"
      fi
    fi
  fi

  SERVICE_STATUS["$status_key"]=$_status
}

######################################################################
# Check functions
######################################################################

check_pacman_wrapper() {
  header "Pacman Wrapper"

  local status="ok"
  local issues=()

  # Check if wrapper is installed
  if [[ -L /usr/bin/pacman ]]; then
    local target
    target=$(readlink -f /usr/bin/pacman)
    if [[ $target == "/usr/local/bin/pacman_wrapper" ]]; then
      msg "Pacman symlink points to wrapper"
    else
      issues+=("Pacman symlink points to: $target (expected /usr/local/bin/pacman_wrapper)")
      status="error"
    fi
  else
    issues+=("Pacman is not a symlink (wrapper not installed)")
    status="error"
  fi

  # Check if original pacman is backed up
  if [[ -f /usr/bin/pacman.orig ]]; then
    msg "Original pacman backed up at /usr/bin/pacman.orig"
  else
    issues+=("Original pacman backup not found at /usr/bin/pacman.orig")
    status="error"
  fi

  # Check if wrapper script exists
  if [[ -f /usr/local/bin/pacman_wrapper ]]; then
    msg "Wrapper script exists at /usr/local/bin/pacman_wrapper"
  else
    issues+=("Wrapper script not found at /usr/local/bin/pacman_wrapper")
    status="error"
  fi

  # Check supporting files
  for file in words.txt pacman_blocked_keywords.txt pacman_whitelist.txt; do
    if [[ -f "/usr/local/bin/$file" ]]; then
      msg "Supporting file exists: /usr/local/bin/$file"
    else
      warn "Supporting file missing: /usr/local/bin/$file"
    fi
  done

  # Report and fix
  if [[ $status == "error" ]]; then
    for issue in "${issues[@]}"; do
      err "$issue"
    done
    ((ISSUES_FOUND++)) || true

    if [[ $STATUS_ONLY -eq 0 ]]; then
      note "Installing pacman wrapper..."
      if [[ -f $PACMAN_WRAPPER_INSTALL ]]; then
        run bash "$PACMAN_WRAPPER_INSTALL"
        ((FIXES_APPLIED++)) || true
        # Re-verify after fix
        if [[ $DRY_RUN -eq 0 ]] && [[ -L /usr/bin/pacman ]] && [[ -f /usr/bin/pacman.orig ]] && [[ -f /usr/local/bin/pacman_wrapper ]]; then
          status="ok"
        fi
      else
        err "Installer script not found: $PACMAN_WRAPPER_INSTALL"
      fi
    fi
  fi

  SERVICE_STATUS["pacman_wrapper"]=$status
}

check_midnight_shutdown() {
  header "Midnight Shutdown (Day-Specific Auto-Shutdown)"

  local status="ok"
  local issues=()

  # Check timer
  if systemctl is-enabled day-specific-shutdown.timer &> /dev/null; then
    msg "day-specific-shutdown.timer is enabled"
  else
    issues+=("day-specific-shutdown.timer is not enabled")
    status="error"
  fi

  if systemctl is-active day-specific-shutdown.timer &> /dev/null; then
    msg "day-specific-shutdown.timer is active"
  else
    issues+=("day-specific-shutdown.timer is not active")
    status="warning"
  fi

  # Check service file exists
  if [[ -f /etc/systemd/system/day-specific-shutdown.service ]]; then
    msg "day-specific-shutdown.service file exists"
  else
    issues+=("day-specific-shutdown.service file missing")
    status="error"
  fi

  # Check management script
  if [[ -f /usr/local/bin/day-specific-shutdown-manager.sh ]]; then
    msg "Shutdown manager script exists"
  else
    issues+=("day-specific-shutdown-manager.sh not found")
    status="error"
  fi

  report_and_fix issues status "midnight_shutdown" \
    "Setting up midnight shutdown..." \
    "$MIDNIGHT_SHUTDOWN_SCRIPT" \
    "day-specific-shutdown.timer" \
    enable
}

check_startup_monitor() {
  header "PC Startup Monitor"

  local status="ok"
  local issues=()

  # Check timer (the timer triggers the service, so we check the timer)
  if systemctl is-enabled pc-startup-monitor.timer &> /dev/null; then
    msg "pc-startup-monitor.timer is enabled"
  else
    issues+=("pc-startup-monitor.timer is not enabled")
    status="error"
  fi

  if systemctl is-active pc-startup-monitor.timer &> /dev/null; then
    msg "pc-startup-monitor.timer is active"
  else
    issues+=("pc-startup-monitor.timer is not active")
    status="warning"
  fi

  # Check service file exists
  if [[ -f /etc/systemd/system/pc-startup-monitor.service ]]; then
    msg "pc-startup-monitor.service file exists"
  else
    issues+=("pc-startup-monitor.service file missing")
    status="error"
  fi

  # Check monitor script
  if [[ -f /usr/local/bin/pc-startup-check.sh ]]; then
    msg "Startup check script exists"
  else
    issues+=("pc-startup-check.sh not found")
    status="error"
  fi

  report_and_fix issues status "startup_monitor" \
    "Setting up startup monitor..." \
    "$STARTUP_MONITOR_SCRIPT" \
    "pc-startup-monitor.timer"
}

check_periodic_systems() {
  header "Periodic System Maintenance"

  local status="ok"
  local issues=()

  # Check timer
  if systemctl is-enabled periodic-system-maintenance.timer &> /dev/null; then
    msg "periodic-system-maintenance.timer is enabled"
  else
    issues+=("periodic-system-maintenance.timer is not enabled")
    status="error"
  fi

  if systemctl is-active periodic-system-maintenance.timer &> /dev/null; then
    msg "periodic-system-maintenance.timer is active"
  else
    issues+=("periodic-system-maintenance.timer is not active")
    status="warning"
  fi

  # Check startup service
  if systemctl is-enabled periodic-system-startup.service &> /dev/null; then
    msg "periodic-system-startup.service is enabled"
  else
    issues+=("periodic-system-startup.service is not enabled")
    status="error"
  fi

  # Check hosts file monitor
  if systemctl is-enabled hosts-file-monitor.service &> /dev/null; then
    msg "hosts-file-monitor.service is enabled"
  else
    issues+=("hosts-file-monitor.service is not enabled")
    status="error"
  fi

  if systemctl is-active hosts-file-monitor.service &> /dev/null; then
    msg "hosts-file-monitor.service is active"
  else
    issues+=("hosts-file-monitor.service is not active")
    status="warning"
  fi

  # Check maintenance script
  if [[ -f /usr/local/bin/periodic-system-maintenance.sh ]]; then
    msg "Maintenance script exists"
  else
    issues+=("periodic-system-maintenance.sh not found")
    status="error"
  fi

  report_and_fix issues status "periodic_systems" \
    "Setting up periodic systems..." \
    "$PERIODIC_SYSTEM_SCRIPT" \
    "periodic-system-maintenance.timer"
}

check_hosts() {
  header "Hosts File and Guards"

  local status="ok"
  local issues=()

  # Check /etc/hosts exists and has content
  if [[ -f /etc/hosts ]]; then
    local line_count
    line_count=$(wc -l < /etc/hosts)
    if [[ $line_count -gt 100 ]]; then
      msg "/etc/hosts exists with $line_count lines (StevenBlack list likely installed)"
    else
      issues+=("/etc/hosts has only $line_count lines (StevenBlack list may not be installed)")
      status="warning"
    fi
  else
    issues+=("/etc/hosts does not exist")
    status="error"
  fi

  # Check if hosts file is immutable
  local attrs
  attrs=$(lsattr /etc/hosts 2> /dev/null | cut -d' ' -f1 || echo "")
  if [[ $attrs == *"i"* ]]; then
    msg "/etc/hosts has immutable attribute set"
  else
    issues+=("/etc/hosts is not immutable")
    status="warning"
  fi

  # Check cached hosts file
  if [[ -f /etc/hosts.stevenblack ]]; then
    msg "StevenBlack cache exists at /etc/hosts.stevenblack"
  else
    issues+=("StevenBlack cache not found")
    status="warning"
  fi

  # Check hosts guard path watcher
  if systemctl is-enabled hosts-guard.path &> /dev/null; then
    msg "hosts-guard.path is enabled"
  else
    issues+=("hosts-guard.path is not enabled")
    status="error"
  fi

  if systemctl is-active hosts-guard.path &> /dev/null; then
    msg "hosts-guard.path is active"
  else
    issues+=("hosts-guard.path is not active")
    status="warning"
  fi

  # Check hosts bind mount service
  if systemctl is-enabled hosts-bind-mount.service &> /dev/null; then
    msg "hosts-bind-mount.service is enabled"
  else
    issues+=("hosts-bind-mount.service is not enabled")
    status="warning"
  fi

  # Check enforcement script
  if [[ -f /usr/local/sbin/enforce-hosts.sh ]]; then
    msg "Enforcement script exists at /usr/local/sbin/enforce-hosts.sh"
  else
    issues+=("enforce-hosts.sh not found")
    status="error"
  fi

  # Check unlock script
  if [[ -f /usr/local/sbin/unlock-hosts ]]; then
    msg "Unlock script exists at /usr/local/sbin/unlock-hosts"
  else
    issues+=("unlock-hosts not found")
    status="warning"
  fi

  # Check locked hosts snapshot
  if [[ -f /usr/local/share/locked-hosts ]]; then
    msg "Canonical hosts snapshot exists at /usr/local/share/locked-hosts"
  else
    issues+=("Canonical hosts snapshot not found")
    status="error"
  fi

  # Check pacman hooks
  if [[ -f /etc/pacman.d/hooks/10-unlock-etc-hosts.hook ]] && [[ -f /etc/pacman.d/hooks/90-relock-etc-hosts.hook ]]; then
    msg "Pacman hooks installed"
  else
    issues+=("Pacman hooks not installed")
    status="warning"
  fi

  # Report issues
  if [[ $status != "ok" ]]; then
    for issue in "${issues[@]}"; do
      if [[ $status == "error" ]]; then
        err "$issue"
      else
        warn "$issue"
      fi
    done
    ((ISSUES_FOUND++)) || true

    if [[ $STATUS_ONLY -eq 0 ]]; then
      # Run hosts install first
      if [[ ! -f /etc/hosts ]] || [[ $(wc -l < /etc/hosts) -lt 100 ]]; then
        note "Installing hosts file..."
        if [[ -f $HOSTS_INSTALL_SCRIPT ]]; then
          run bash "$HOSTS_INSTALL_SCRIPT"
          ((FIXES_APPLIED++)) || true
        else
          err "Hosts install script not found: $HOSTS_INSTALL_SCRIPT"
        fi
      fi

      # Run hosts guard setup
      if ! systemctl is-enabled hosts-guard.path &> /dev/null || [[ ! -f /usr/local/sbin/enforce-hosts.sh ]]; then
        note "Setting up hosts guard..."
        if [[ -f $HOSTS_GUARD_SCRIPT ]]; then
          run bash "$HOSTS_GUARD_SCRIPT"
          ((FIXES_APPLIED++)) || true
        else
          err "Hosts guard script not found: $HOSTS_GUARD_SCRIPT"
        fi
      fi

      # Install pacman hooks if missing
      if [[ ! -f /etc/pacman.d/hooks/10-unlock-etc-hosts.hook ]]; then
        note "Installing pacman hooks..."
        if [[ -f $HOSTS_PACMAN_HOOKS_SCRIPT ]]; then
          run bash "$HOSTS_PACMAN_HOOKS_SCRIPT"
          ((FIXES_APPLIED++)) || true
        else
          err "Pacman hooks script not found: $HOSTS_PACMAN_HOOKS_SCRIPT"
        fi
      fi

      # Re-verify after fixes
      if [[ $DRY_RUN -eq 0 ]]; then
        if systemctl is-enabled hosts-guard.path &> /dev/null &&
          [[ -f /usr/local/sbin/enforce-hosts.sh ]] &&
          [[ -f /usr/local/share/locked-hosts ]] &&
          [[ -f /etc/pacman.d/hooks/10-unlock-etc-hosts.hook ]]; then
          # Downgrade to warning if only minor issues remain (immutable attr, etc.)
          status="ok"
        fi
      fi
    fi
  fi

  SERVICE_STATUS["hosts"]=$status
}

######################################################################
# Summary
######################################################################
print_summary() {
  header "Summary"

  echo ""
  printf "%-25s %s\n" "Service" "Status"
  printf "%-25s %s\n" "-------" "------"

  for service in pacman_wrapper midnight_shutdown startup_monitor periodic_systems hosts; do
    local status="${SERVICE_STATUS[$service]:-unknown}"
    local color
    case "$status" in
      ok) color=$GREEN ;;
      warning) color=$YELLOW ;;
      error) color=$RED ;;
      *) color=$NC ;;
    esac
    printf "%-25s ${color}%s${NC}\n" "$service" "$status"
  done

  echo ""
  if [[ $DRY_RUN -eq 1 ]]; then
    note "DRY RUN - No changes were made"
  fi

  if [[ $ISSUES_FOUND -eq 0 ]]; then
    msg "All services are properly configured!"
  else
    if [[ $STATUS_ONLY -eq 1 ]]; then
      warn "Found $ISSUES_FOUND service(s) with issues"
      note "Run without --status to fix issues"
    else
      if [[ $FIXES_APPLIED -gt 0 ]]; then
        msg "Applied $FIXES_APPLIED fix(es)"
      else
        warn "Found $ISSUES_FOUND issue(s) but no fixes were applied"
      fi
    fi
  fi
}

######################################################################
# Main
######################################################################
main() {
  echo ""
  echo "Digital Wellbeing Services Status Check"
  echo "========================================"
  echo "Date: $(date)"
  echo "User: ${SUDO_USER:-$USER}"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "Mode: DRY RUN (no changes will be made)"
  elif [[ $STATUS_ONLY -eq 1 ]]; then
    echo "Mode: STATUS ONLY (no changes will be made)"
  else
    echo "Mode: CHECK AND FIX"
  fi

  check_pacman_wrapper
  check_midnight_shutdown
  check_startup_monitor
  check_periodic_systems
  check_hosts

  print_summary
}

main
