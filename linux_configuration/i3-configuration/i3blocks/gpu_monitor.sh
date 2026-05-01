#!/bin/bash
# i3blocks GPU monitor, persist mode.
#
# Keeps a single long-lived `nvidia-smi --loop=5` (or reads amdgpu sysfs
# in a blocking-read loop) instead of forking nvidia-smi/lspci/awk/tr/bc
# every interval. No sleep, no polling loop in bash — nvidia-smi's own
# periodic emitter drives updates and we block on `read`.
#
# Configure with `interval=persist` and `markup=pango` in the i3blocks
# config. In persist mode each newline is a separate status update, so
# we emit exactly ONE line (with inline pango markup for color).

set -u

# Nerd Font glyph: display / desktop icon (U+F108).
ICON=$'\uf108'

emit() {
  local temp=$1 load=$2 color
  if [[ $load == 'N/A' ]]; then
    color='#FFFFFF'
  elif ((load < 50)); then
    color='#50FA7B'
  elif ((load < 75)); then
    color='#F1FA8C'
  else
    color='#FF5555'
  fi
  printf '<span color="%s">%s    %s°C, %s%%</span>\n' \
    "$color" "$ICON" "$temp" "$load"
}

# Prefer NVIDIA if present (persist via --loop).
if command -v nvidia-smi > /dev/null 2>&1; then
  # One child process for the lifetime of i3blocks; emits CSV every 5s.
  nvidia-smi \
    --query-gpu=temperature.gpu,utilization.gpu \
    --format=csv,noheader,nounits \
    --loop=5 2> /dev/null |
    while IFS=',' read -r temp load; do
      # Strip leading/trailing whitespace using parameter expansion.
      temp=${temp## }
      temp=${temp%% }
      load=${load## }
      load=${load%% }
      [[ -z $temp || -z $load ]] && continue
      emit "$temp" "$load"
    done
  exit 0
fi

# AMD fallback: read sysfs directly; emit once (i3blocks restarts on exit).
amdgpu=''
for d in /sys/class/hwmon/hwmon*/; do
  [[ -r ${d}name ]] || continue
  read -r n < "${d}name"
  [[ $n == amdgpu ]] && {
    amdgpu=$d
    break
  }
done
if [[ -n $amdgpu ]]; then
  temp='N/A'
  if [[ -r ${amdgpu}temp1_input ]]; then
    read -r milli < "${amdgpu}temp1_input"
    temp=$((milli / 1000))
  fi
  load='N/A'
  # drm card matching the amdgpu hwmon exposes gpu_busy_percent.
  for card in /sys/class/drm/card*/device/gpu_busy_percent; do
    [[ -r $card ]] && {
      read -r load < "$card"
      break
    }
  done
  emit "$temp" "$load"
  exit 0
fi

printf '<span color="#FF5555">%s No supported GPU</span>\n' "$ICON"
