#!/usr/bin/env bash
# Package-installation helpers for the fresh-install run.
#
# Sourced by main.sh, which owns the ordering of the top-level steps; this
# file defines functions only, so sourcing it has no side effects.

# Function to play a sound on error
play_error_sound() {
  #pactl set-sink-volume @DEFAULT_SINK@ +50%
  for _ in 1 2 3; do
    paplay /usr/share/sounds/freedesktop/stereo/dialog-error.oga
  done
  #pactl set-sink-volume @DEFAULT_SINK@ -50%
}

install_from_aur() {
  local repo_url pkg_name repo_dir
  repo_url="$1"
  pkg_name="$2"

  mkdir -p "$HOME/aur"
  cd "$HOME/aur" || return 1
  repo_dir="$(basename "$repo_url" .git)"

  if [ ! -d "$repo_dir" ]; then
    git clone "$repo_url"
  else
    echo "Repository $repo_dir already cloned; updating"
    (cd "$repo_dir" && git fetch --all -q && git reset --hard origin/HEAD -q || git pull --ff-only || true)
  fi
  cd "$repo_dir" || return 1

  if pacman -Qi "$pkg_name" > /dev/null 2>&1; then
    echo "$pkg_name is already installed"
    return 0
  fi

  echo "Cleaning old package artifacts to avoid duplicate -U targets"
  find . -maxdepth 1 -type f -name '*.pkg.tar.*' -delete 2> /dev/null || true

  echo "Building $pkg_name (clean build)"
  # -c (clean up work dirs after) -C (clean build - remove src/ and pkg/ first)
  if ! yes | makepkg -s -c -C --noconfirm --nocheck --skipchecksums --skipinteg --skippgpcheck --needed; then
    echo "Build failed for $pkg_name" >&2
    return 1
  fi

  # Collect only the freshly built packages (should now be only current version)
  mapfile -t built_pkgs < <(find . -maxdepth 1 -type f -name '*.pkg.tar.zst' -printf './%f\n')
  if [ ${#built_pkgs[@]} -eq 0 ]; then
    echo "No package files produced for $pkg_name" >&2
    return 1
  fi

  echo "Installing built package(s): ${built_pkgs[*]}"
  if ! yes | sudo pacman -U --noconfirm "${built_pkgs[@]}"; then
    echo "Installation failed for $pkg_name" >&2
    return 1
  fi
}

# Helper: try to install from AUR and log result to done.txt/failed.txt
try_aur_install() {
  local repo_url="$1"
  local pkg_name="$2"
  if install_from_aur "$repo_url" "$pkg_name"; then
    echo "$pkg_name" >> done.txt
  else
    echo "$pkg_name" >> failed.txt
  fi
}

process_packages() {
  local file_path
  file_path="$1"
  : > failed.txt
  : > done.txt

  while IFS= read -r pkg_name; do
    if [ -z "$pkg_name" ]; then
      continue
    fi

    local repo_url repo_dir
    repo_url="https://aur.archlinux.org/${pkg_name}-git.git"
    repo_dir="${pkg_name}-git"

    git clone "$repo_url"
    if [ -d "$repo_dir" ] && [ -z "$(ls -A "$repo_dir")" ]; then
      echo "Repository $repo_dir is empty, trying without -git suffix"
      repo_url="https://aur.archlinux.org/${pkg_name}.git"
      repo_dir="${pkg_name}"

      git clone "$repo_url"
      if [ -d "$repo_dir" ] && [ -z "$(ls -A "$repo_dir")" ]; then
        echo "Repository $repo_dir is empty, trying to install with pacman"
        if sudo pacman -Sy --noconfirm "$pkg_name"; then
          echo "$pkg_name" >> done.txt
        else
          echo "$pkg_name" >> failed.txt
        fi
      else
        try_aur_install "$repo_url" "$pkg_name"
      fi
    else
      try_aur_install "$repo_url" "$pkg_name"
    fi
  done < "$file_path"
}

# Helper: Check if all subpackages are installed
# Returns 0 if ALL subpackages are installed, 1 otherwise
all_subpackages_installed() {
  local -n sub_pkgs_ref=$1
  for subpkg in "${sub_pkgs_ref[@]}"; do
    if ! pacman -Qi "$subpkg" &> /dev/null; then
      return 1
    fi
  done
  return 0
}
