#!/usr/bin/env bash

# Fixture: the pre-split installer. Places three files under $HOME.
#
# Its partner, dropped_write_after.sh, is the "split" version that silently
# loses one of them -- the exact failure --prefix exists to catch. Without the
# manifest section, a dropped `cat >` shows up as NOTHING at all: same exit
# status, same stubbed calls, same stdout. The traces match and the bug ships.

set -euo pipefail

bin_dir="$HOME/.local/bin"
unit_dir="$HOME/.config/systemd/user"
mkdir -p "$bin_dir" "$unit_dir"

cat >"$bin_dir/demo-agent.sh" <<'SCRIPT'
#!/usr/bin/env bash
echo "demo agent running"
SCRIPT
chmod +x "$bin_dir/demo-agent.sh"

cat >"$unit_dir/demo-agent.service" <<'UNIT'
[Unit]
Description=Demo agent

[Service]
ExecStart=%h/.local/bin/demo-agent.sh
UNIT

cat >"$unit_dir/demo-agent.timer" <<'UNIT'
[Unit]
Description=Demo agent timer

[Timer]
OnCalendar=hourly
UNIT

systemctl --user daemon-reload
echo "install complete"
