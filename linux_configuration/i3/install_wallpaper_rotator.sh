#!/bin/bash
# Install the wallpaper rotator: Earth images, the systemd user service and
# its 15-minute timer, then run one tick. Rerunnable: images are kept, units
# are re-linked.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly UNIT="wallpaper-rotator"
readonly EARTH_DIR="${HOME}/.cache/wallpaper_rotator/earth"
readonly NASA="https://assets.science.nasa.gov/content/dam/science/esd/eo/images"
# NASA Earth Observatory, public domain: Blue Marble Next Generation
# (December, topography + bathymetry) and Black Marble 2012 night lights.
readonly DAY_URL="${NASA}/bmng/bmng-topography-bathymetry/december/world.topo.bathy.200412.3x5400x2700.jpg"
readonly NIGHT_URL="${NASA}/imagerecords/79000/79765/dnb_land_ocean_ice.2012.3600x1800.jpg"

ensure_packages() {
	local missing=()
	command -v feh >/dev/null || missing+=(feh)
	/usr/bin/python3 -c 'import numpy' 2>/dev/null || missing+=(python-numpy)
	/usr/bin/python3 -c 'import PIL' 2>/dev/null || missing+=(python-pillow)
	if ((${#missing[@]})); then
		sudo pacman -S --needed --noconfirm "${missing[@]}"
	fi
}

fetch() {
	local url="$1" dest="$2"
	[[ -s "$dest" ]] && return 0
	curl -fsSL --retry 3 -o "${dest}.part" "$url"
	mv "${dest}.part" "$dest"
}

main() {
	ensure_packages
	mkdir -p "$EARTH_DIR" "${HOME}/.config/systemd/user"
	fetch "$DAY_URL" "${EARTH_DIR}/day.jpg"
	fetch "$NIGHT_URL" "${EARTH_DIR}/night.jpg"
	local kind
	for kind in service timer; do
		ln -sf "${SCRIPT_DIR}/${UNIT}.${kind}" "${HOME}/.config/systemd/user/${UNIT}.${kind}"
	done
	systemctl --user daemon-reload
	systemctl --user enable --now "${UNIT}.timer"
	systemctl --user start "${UNIT}.service"
	echo "wallpaper-rotator timer: $(systemctl --user is-active "${UNIT}.timer")"
}

main "$@"
