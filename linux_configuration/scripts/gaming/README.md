## Dual Steam Accounts (same PC, two monitors)

Runs a second Steam instance as `player2` on HDMI-0, alongside your main session on DP-0.
Both accounts play simultaneously with full GPU acceleration — no VT switching needed.

### One-time setup (fresh install)

**1. Create the player2 user:**
```bash
sudo useradd -m -G audio,video,input -s /bin/bash player2
sudo passwd player2
```

**2. Install dependencies:**
```bash
sudo pacman -S xorg-xhost
```

**3. Add passwordless sudoers rule** (allows launching Steam as player2 without a prompt):
```bash
echo "kuhy ALL=(player2) NOPASSWD: /usr/bin/steam" | sudo tee /etc/sudoers.d/player2-steam
sudo chmod 440 /etc/sudoers.d/player2-steam
```

**4. Symlink the script into PATH:**
```bash
sudo ln -sf ~/testsAndMisc/linux_configuration/scripts/gaming/start-player2.sh /usr/local/bin/start-player2
```

**5. Start the getty on tty2** (needed if LightDM autologin is configured, otherwise tty2 has no login prompt):
```bash
sudo systemctl enable getty@tty2
```

### Usage

```bash
start-player2
```

A Steam window opens as `player2`. Drag it to HDMI-0 and log into the second account.
Click whichever monitor you want to control — no switching needed.

To stop: close the Steam window or `pkill -u player2 -f steam`.

### How it works

- Steam is launched as `player2` via `sudo -H -u player2 steam` on `DISPLAY=:0` (your main X session).
- Because `player2` has a separate home directory (`~/.local/share/Steam/`), the two Steam
  instances don't conflict — different PID locks, different configs, different accounts.
- `xhost +local:` grants local users access to your X display.
- Full GPU acceleration since there is no nesting — both instances hit the hardware directly.

### Monitor layout

| Output | Resolution | Session      |
|--------|------------|--------------|
| DP-0   | 3840×2160  | kuhy (main)  |
| HDMI-0 | 2560×1440  | player2      |
