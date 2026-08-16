#!/usr/bin/env bash

# Fixture: writes addressed through XDG_* rather than through $HOME.
#
# --prefix exports XDG_DATA_HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME and
# XDG_STATE_HOME explicitly instead of letting them default off HOME. This
# fixture is what makes that claim measurable: all four writes must appear in
# the manifest under the prefix.
#
# Why it matters beyond tidiness: install_leechblock.sh reads XDG_DATA_HOME
# directly and then runs `rsync -a --delete` at the result. If the harness
# redirected only HOME, a real XDG_DATA_HOME inherited from the caller's
# environment would still point at live data -- and --delete would empty it.
# Proving the redirect here costs nothing; proving it by running the installer
# would risk exactly the loss being guarded against.

set -euo pipefail

data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/xdg-fixture"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/xdg-fixture"
cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/xdg-fixture"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/xdg-fixture"
mkdir -p "$data_dir" "$config_dir" "$cache_dir" "$state_dir"

printf 'data\n' >"$data_dir/payload"
printf 'config\n' >"$config_dir/settings.conf"
printf 'cache\n' >"$cache_dir/entry"
printf 'state\n' >"$state_dir/last-run"

echo "wrote four XDG-addressed files"
