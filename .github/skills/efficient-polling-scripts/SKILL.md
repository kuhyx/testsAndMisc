---
name: efficient-polling-scripts
description: Use BEFORE writing any shell or Python script that runs on a timer, per-tick status bar (i3blocks/waybar/polybar), cron-like loop, or any repeated invocation. Prevents fork-storm anti-patterns that can consume many CPU-hours per day from tiny polling scripts.
---

# Efficient Polling & Status-Bar Scripts

## When this applies

Any script that runs **frequently** — per second or per few seconds — especially:

- i3blocks / waybar / polybar / xmobar / tmux status-line scripts
- cron / systemd-timer jobs with intervals < 1 min
- watcher loops invoked by another process every tick
- Python CLIs invoked from a shell hot loop

A single fork pipeline running once per second will consume ~30–50 CPU-minutes per day per forked helper. Five such scripts with 3–8 helpers each turn into **days of CPU-time lost per day** and tens of thousands of forked processes showing up in `atop`.

## The rules

### R1. Zero forks in the hot path when possible

Every `$(...)`, backtick, and `|` in a shell script forks a process. Favor bash builtins:

| Instead of                      | Use                                                                                 |
| ------------------------------- | ----------------------------------------------------------------------------------- |
| `$(cat /proc/loadavg)`          | `$(</proc/loadavg)` or `read -r one _ < /proc/loadavg`                              |
| `echo "$x" \| awk '{print $1}'` | `read -r first _ <<< "$x"` or `arr=($x); first=${arr[0]}`                           |
| `echo "$x" \| tr -d '%'`        | `${x//%/}`                                                                          |
| `echo "$x" \| grep -Po '\d+%'`  | `[[ $x =~ ([0-9]+)% ]] && vol=${BASH_REMATCH[1]}`                                   |
| `echo "$a < $b" \| bc -l`       | `(( a_times_100 < b_times_100 ))` (scale decimals to ints)                          |
| `sensors \| awk ...`            | `read -r milli < /sys/class/hwmon/hwmonN/temp1_input`                               |
| `acpi -b \| awk ...`            | `read -r cap < /sys/class/power_supply/BAT0/capacity`                               |
| `free -h \| awk ...`            | parse `/proc/meminfo` with `while read -r`                                          |
| `df -h / \| awk ...`            | `stat -f` builtin? No: use a long-lived reader, or accept one fork at low frequency |
| `lspci \| grep -i nvidia`       | check `/sys/bus/pci/devices/*/vendor` (0x10de == NVIDIA)                            |

### R2. Read from /sys and /proc directly

The kernel exposes structured data without forking anything. Useful paths:

- CPU load: `/proc/loadavg`
- CPU per-core stat: `/proc/stat`
- Memory: `/proc/meminfo`
- Temps / fans / voltages: `/sys/class/hwmon/hwmon*/`
  - CPU on AMD: `name=k10temp`, `temp1_input` = Tctl (milli-°C, divide by 1000)
  - CPU on Intel: `name=coretemp`
  - Motherboard Super-I/O: `name=nct*` / `it87*` / `f71*`
  - AMD GPU: `name=amdgpu`, plus `/sys/class/drm/card*/device/gpu_busy_percent`
- Battery: `/sys/class/power_supply/BAT*/` (`capacity`, `status`, `energy_now`, `power_now`)
- Backlight: `/sys/class/backlight/*/brightness`
- Network link: `/sys/class/net/*/operstate`, `/sys/class/net/*/statistics/*_bytes`

NVIDIA is the unfortunate exception — there is no sysfs utilization interface, so `nvidia-smi` is required. Mitigate with **R4** (long-lived producer).

### R3. Integer arithmetic, never `bc` in a hot loop

`bc` forks a process. For decimal comparisons, multiply out:

```bash
# "1.23" → 123, "0.45" → 45; compare against threshold ×100.
load_x100=$((10#${one//./}))
(( load_x100 < 150 )) && echo 'normal'
```

Bash's `((…))` and `[[ … ]]` are builtins — free.

### R4. Prefer event-driven / long-lived producers over polling + sleep

When an update needs to happen often, replace "poll + sleep + exit" with one of:

- **i3blocks `interval=persist`**: script runs forever, prints one block per update. Block on an event stream with `read` — no sleep, no busy-wait.
- **`pactl subscribe`**: event stream for PulseAudio/PipeWire volume/mute changes.
- **`udevadm monitor`**: hardware / power-supply / backlight events.
- **`inotifywait -m`**: file/dir changes.
- **`dbus-monitor`**: session-wide events (network, media keys, NetworkManager).
- **`journalctl -f`**: new log lines.
- **`nvidia-smi --loop=N`** / **`nvidia-smi dmon -d N`**: one long-lived nvidia-smi emitting rows instead of forking every N seconds. Tail its stdout with `while read`.
- **`mpstat N`**, **`iostat N`**, **`vmstat N`**: same pattern for CPU/IO.

Canonical persist skeleton:

```bash
#!/bin/bash
set -u
emit() { printf '%s\n' "$1"; }

emit "$(initial_value)"
producer_command | while read -r line; do
  # `read` blocks on I/O — no CPU, no sleep, no poll.
  [[ $line matches relevant event ]] || continue
  emit "$(compute_new_value)"
done
```

### R5. One-shot scripts must still be cheap

Even with `interval=5`, 1728 invocations/day × 3 forks = 5k forks/day. Make the single-invocation path fork-free when possible. Profile with:

```bash
strace -f -e trace=%process -c ./myscript.sh
```

The `clone` / `execve` counts are your fork count.

### R6. Python called from a hot loop is an anti-pattern

CPython startup is ~50–80 ms on modern hardware. Invoking `python my_helper.py` once per second = ~5–8% of one core doing nothing but importing stdlib.

If a status-bar value needs Python logic:

- **Inline it in bash** when possible (the rules above almost always suffice).
- **Run a persistent Python daemon** that writes to a FIFO / Unix socket / tmpfile; the bash hot-path reads from it with `read` / `$(<file)`.
- **Use a compiled helper** (Go/Rust/C) if Python startup is the only issue — a static binary startup is sub-millisecond.

### R7. Cap risk with a systemd slice

Even a correct script can regress. Put status-bar / monitoring work in a resource-capped user slice so the blast radius is bounded:

```ini
# ~/.config/systemd/user/monitors.slice
[Slice]
CPUQuota=50%
MemoryMax=512M
MemorySwapMax=0   # REQUIRED on zram systems — see oom-prevention skill
TasksMax=256
```

Launch i3blocks (or individual persist scripts) under that slice, e.g. via a user service with `Slice=monitors.slice`, so every child inherits the cap.

### R8. Measure before and after

For any "fast" shell script, time 10k invocations:

```bash
time for _ in {1..10000}; do ./script.sh >/dev/null; done
```

Target: a 1-Hz script should take < 2 ms per invocation on a modern desktop.
A 5-second-interval script can afford ~20 ms.
If you're over budget, count the `execve` with `strace -c` and remove forks.

## Python-specific rules (for daemons, not hot-loop callees)

- Use `pathlib.Path.read_text()` / `read_bytes()` — one syscall, no subprocess.
- Open `/sys` / `/proc` files with the builtin `open()`; they're tiny reads.
- For event loops, use `asyncio` / `selectors` to block on fds (same idea as `read` in bash) instead of `time.sleep()` in a polling loop.
- Don't shell out with `subprocess.run("sensors")` when `/sys/class/hwmon` exists.
- Cache `psutil` objects across ticks — `psutil.cpu_percent(interval=None)` uses deltas and is O(1) after the first call.

## Common red flags (search for these in review)

- `while true` / `while :` with a `sleep` and no event source
- `$(…|…|…)` chains with three or more pipes in a status-bar script
- `| awk`, `| grep`, `| tr`, `| cut`, `| sed`, `| head`, `| tail` where bash builtins would do
- `$(cat foo)` anywhere — always replaceable with `$(<foo)`
- `echo … | bc` — replaceable with bash integer math
- `sensors`, `acpi`, `free`, `lspci`, `iwgetid` in a per-second script
- `python …` / `node …` invoked per tick
- No `set -u` (silent typo bugs compound over thousands of ticks)

## Verification checklist before shipping

1. `shellcheck script.sh` — clean.
2. `strace -c -f script.sh 2>&1 | grep -E 'execve|clone'` — fork count matches expectation.
3. `time for _ in {1..10000}; do script.sh >/dev/null; done` — under budget.
4. For persist scripts: run for 60 s under `perf stat -p $PID` — CPU time near zero when idle.
5. Running under the `monitors.slice` unit — verify with `systemctl --user status monitors.slice`.

## Reference implementations in this repo

- `linux_configuration/i3-configuration/i3blocks/volume.sh` — persist mode with `pactl subscribe`.
- `linux_configuration/i3-configuration/i3blocks/gpu_monitor.sh` — persist mode with `nvidia-smi --loop`.
- `linux_configuration/i3-configuration/i3blocks/battery_status.sh` — zero-fork via `/sys/class/power_supply`.
- `linux_configuration/i3-configuration/i3blocks/cpu_monitor.sh` — zero-fork via `/proc/loadavg` + `/sys/class/hwmon`.
- `linux_configuration/i3-configuration/i3blocks/motherboard_temp.sh` — zero-fork via `/sys/class/hwmon`.
- `linux_configuration/scripts/system-maintenance/systemd/monitors.slice` — resource-cap slice.
