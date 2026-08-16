# Pacman Wrapper Security Enhancements

## Overview

This document describes the security enhancements made to the pacman wrapper to prevent circumvention, particularly for VirtualBox installations.

## Problem Statement

The original pacman wrapper had the following vulnerabilities:

1. **Easy Policy Bypass**: Users could edit `pacman_greylist.txt` or `pacman_blocked_keywords.txt` to remove restrictions, then reinstall the wrapper.
2. **VirtualBox Hosts Bypass**: VirtualBox VMs do not inherit the host machine's `/etc/hosts` file, allowing users to bypass content filtering within VMs.
3. **No Tamper Detection**: The wrapper had no mechanism to detect if policy files had been modified.

## Solutions Implemented

### 1. Policy File Integrity Checks

**File**: `scripts/periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh`

The installer now:

- Generates SHA256 checksums of all policy files during installation
- Stores checksums in `/var/lib/pacman-wrapper/policy.sha256`
- Makes the integrity file immutable using `chattr +i`
- Makes policy files (`pacman_blocked_keywords.txt`, `pacman_greylist.txt`) immutable

**File**: `scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh`

The wrapper now:

- Verifies policy file integrity on **every invocation**
- Compares current file checksums against stored checksums
- **Blocks all operations** if tampering is detected
- Displays security warnings and instructs user to reinstall

**Benefits**:

- Cannot bypass restrictions by editing policy files
- Tampering is immediately detected and blocked
- Must use `chattr -i` (requires root) to modify files, making bypass harder

### 2. Hardcoded VirtualBox Restrictions

**File**: `scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh`

Added hardcoded VirtualBox detection that **cannot be bypassed** by editing policy files:

```bash
function is_virtualbox_package() {
  local pkg_lower="${1,,}"
  [[ $pkg_lower == *"virtualbox"* || $pkg_lower == *"vbox"* ]]
}
```

This function:

- Is compiled into the wrapper code itself
- Cannot be disabled by editing text files
- Catches all VirtualBox-related packages

**Enhanced Challenge**:

- 7-letter words (harder than greylist's 6-letter words)
- 150 words to memorize (more than greylist's 120)
- 120-second timeout (longer than greylist's 90s)
- 45-second initial delay (psychological friction)
- 30-50 second post-challenge delay

**Warning Messages**:

- Explicit warning about /etc/hosts bypass potential
- Lists security measures that will be applied
- Emphasizes that restrictions are hardcoded

### 3. VirtualBox Hosts Enforcement

**File**: `scripts/periodic_background/digital_wellbeing/virtualbox/enforce_vbox_hosts.sh`

A new enforcement script that:

**For Host Configuration**:

- Configures all VMs to use host's DNS resolution (`--natdnshostresolver1 on`)
- Enables NAT DNS proxy (`--natdnsproxy1 on`)
- Adds `/etc` as a read-only shared folder to all VMs
- Tracks enforcement status with marker file

**For Guest Configuration**:

- Generates a startup script for VMs
- Mounts the shared `/etc` folder inside the VM
- Syncs host's `/etc/hosts` to VM's `/etc/hosts`
- Makes the hosts file read-only in the VM

**Commands**:

```bash
# Apply enforcement to all VMs
sudo enforce_vbox_hosts.sh enforce

# Check enforcement status
sudo enforce_vbox_hosts.sh status

# Generate script for VM guests
sudo enforce_vbox_hosts.sh generate-script
```

**Auto-Integration**:
The pacman wrapper automatically:

- Detects VirtualBox installation after any install operation
- Locates and runs the enforcement script
- Applies enforcement to all existing VMs
- Creates enforcement marker to avoid repeated runs

### 4. Installation Integration

**File**: `scripts/periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh`

The installer now:

- Installs VirtualBox enforcement script to `/usr/local/share/digital_wellbeing/virtualbox/`
- Makes the enforcement script executable
- Reports installation status to user

## Security Guarantees

### What's Protected

1. **Policy files cannot be easily modified**:
   - Immutable attribute prevents casual editing
   - Requires `chattr -i` which requires root and knowledge
   - Changes are detected on next wrapper invocation

2. **VirtualBox restrictions are hardcoded**:
   - Cannot remove by editing policy files
   - Would require modifying the wrapper code itself
   - Integrity checks would detect wrapper modification

3. **VMs inherit host's content filtering**:
   - DNS queries use host's resolution
   - /etc/hosts is synced from host to guest
   - Read-only mounting prevents VM modification

### What's Still Vulnerable

1. **Root access can bypass everything**:
   - Root can `chattr -i` and modify files
   - Root can edit the wrapper script itself
   - Root can disable enforcement entirely
   - **Mitigation**: Not the goal; this is about self-discipline, not security against root

2. **Wrapper replacement**:
   - Could replace `/usr/bin/pacman` with direct link to `/usr/bin/pacman.orig`
   - **Mitigation**: Periodic maintenance services can detect and alert
   - Reinstallation would fail integrity check if files are modified

3. **VM Guest Additions bypass**:
   - If guest doesn't install VBox Guest Additions, shared folders won't work
   - **Mitigation**: DNS proxy still enforces host's DNS resolution
   - Manual hosts file sync would be needed

## More detail

Split out to stay under the 250-line cap.

- [Testing, usage and design philosophy](pacman-wrapper/testing-and-usage.md)
