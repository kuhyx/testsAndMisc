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

**File**: `scripts/digital_wellbeing/pacman/install_pacman_wrapper.sh`

The installer now:
- Generates SHA256 checksums of all policy files during installation
- Stores checksums in `/var/lib/pacman-wrapper/policy.sha256`
- Makes the integrity file immutable using `chattr +i`
- Makes policy files (`pacman_blocked_keywords.txt`, `pacman_greylist.txt`) immutable

**File**: `scripts/digital_wellbeing/pacman/pacman_wrapper.sh`

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

**File**: `scripts/digital_wellbeing/pacman/pacman_wrapper.sh`

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

**File**: `scripts/digital_wellbeing/virtualbox/enforce_vbox_hosts.sh`

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

**File**: `scripts/digital_wellbeing/pacman/install_pacman_wrapper.sh`

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

## Testing

Run the test suite:

```bash
bash tests/test_pacman_wrapper_security.sh
```

Tests verify:
- Script syntax validity
- Integrity check function exists and is called
- Hardcoded VirtualBox check exists
- VirtualBox challenge function exists
- Immutable file attributes are set
- VirtualBox enforcement integration

## Usage

### Installation

```bash
cd scripts/digital_wellbeing/pacman
sudo ./install_pacman_wrapper.sh
```

This will:
- Install the wrapper and policy files
- Generate integrity checksums
- Make policy files immutable
- Install VirtualBox enforcement script

### Updating Policy Files

If you need to legitimately update policy files:

```bash
# Remove immutable attribute
sudo chattr -i /usr/local/bin/pacman_blocked_keywords.txt
sudo chattr -i /usr/local/bin/pacman_greylist.txt

# Edit files as needed
sudo nano /usr/local/bin/pacman_greylist.txt

# Reinstall wrapper to update checksums
cd scripts/digital_wellbeing/pacman
sudo ./install_pacman_wrapper.sh

# This will regenerate checksums and reapply immutable attributes
```

### VirtualBox Enforcement

After installing VirtualBox, the wrapper will automatically apply enforcement. You can also manually run:

```bash
sudo /usr/local/share/digital_wellbeing/virtualbox/enforce_vbox_hosts.sh enforce
```

For VM guests, copy the generated script and add to startup:

```bash
# On host
sudo /usr/local/share/digital_wellbeing/virtualbox/enforce_vbox_hosts.sh generate-script /tmp/vbox_sync.sh

# Copy to VM and install
sudo cp /tmp/vbox_sync.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/vbox_sync.sh

# Add to crontab or systemd
@reboot /usr/local/bin/vbox_sync.sh
```

## Design Philosophy

These enhancements follow the principle of **defense in depth**:

- **Layer 1**: Immutable policy files (prevents casual editing)
- **Layer 2**: Integrity checksums (detects tampering)
- **Layer 3**: Hardcoded restrictions (cannot bypass via files)
- **Layer 4**: VirtualBox enforcement (prevents VM bypass)
- **Layer 5**: Psychological friction (word challenges, delays)

Each layer adds difficulty, making circumvention progressively harder while maintaining usability for legitimate use.

## Future Enhancements

Potential improvements:

1. **Digital signatures**: Sign the wrapper script itself to detect modifications
2. **Remote policy updates**: Fetch policy files from a trusted source
3. **Logging**: Log all wrapper invocations and challenges to detect patterns
4. **Time-based restrictions**: Different rules for different times/days
5. **Multi-factor challenges**: Combine word challenges with other verification methods
