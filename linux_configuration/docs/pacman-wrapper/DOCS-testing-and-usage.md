# Testing, usage and design philosophy

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
cd periodic_background/digital_wellbeing/pacman
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
cd periodic_background/digital_wellbeing/pacman
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
