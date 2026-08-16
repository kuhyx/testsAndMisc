#!/usr/bin/env bash

# Fixture: the BROKEN split of dropped_write_before.sh.
#
# The .timer write was lost -- the kind of thing that happens when a heredoc
# falls across a seam during a split. Everything else is identical: same exit
# status, same stubbed systemctl call, same stdout "install complete".
#
# Diffing a --prefix trace of this against its partner must show the missing
# demo-agent.timer line. That diff is the whole point of the manifest.

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

# The .timer heredoc that belongs here was dropped by the split.

systemctl --user daemon-reload
echo "install complete"
