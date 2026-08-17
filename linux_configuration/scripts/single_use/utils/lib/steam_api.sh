#!/usr/bin/env bash
# Steam library discovery, the Steam and ProtonDB API calls, and requirement
# extraction for steam_compatibility.sh.

find_steamapps_dirs() {
  local dirs=()
  for base in "${STEAM_DIRS[@]}"; do
    [[ -d $base ]] || continue
    if [[ -f "$base/steamapps/libraryfolders.vdf" ]]; then
      # Newer format includes nested objects with paths
      local paths
      paths=$(grep -oE '"path"\s+"[^"]+"' "$base/steamapps/libraryfolders.vdf" | sed -E 's/.*"([^"]+)"/\1/' || true)
      if [[ -n $paths ]]; then
        while IFS= read -r p; do
          [[ -d "$p/steamapps" ]] && dirs+=("$p/steamapps")
        done <<< "$paths"
      fi
    fi
    [[ -d "$base/steamapps" ]] && dirs+=("$base/steamapps")
  done
  # de-dupe
  printf "%s\n" "${dirs[@]}" 2> /dev/null | awk '!seen[$0]++'
}

list_installed_games() {
  local d appid name
  while IFS= read -r d; do
    [[ -d $d ]] || continue
    for mf in "$d"/appmanifest_*.acf; do
      [[ -f $mf ]] || continue
      appid=$(grep -oE '"appid"\s+"[0-9]+"' "$mf" | sed -E 's/.*"([0-9]+)"/\1/' | head -n1)
      name=$(grep -oE '"name"\s+"[^"]+"' "$mf" | sed -E 's/.*"([^"]+)"/\1/' | head -n1)
      if [[ -n $appid ]]; then
        printf "%s\t%s\n" "$appid" "${name:-Unknown}"
      fi
    done
  done < <(find_steamapps_dirs)
}

list_owned_games_via_api() {
  local key="${STEAM_API_KEY:-}" sid="${STEAM_ID64:-}"
  if [[ -z $key || -z $sid ]]; then
    return 1
  fi
  local url="https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=${key}&steamid=${sid}&include_appinfo=1&include_played_free_games=1&format=json"
  http_get "$url" | jq -r '.response.games[]? | "\(.appid)\t\(.name)"' || return 1
}

fetch_appdetails_json() {
  local appid="$1"
  # Using store API (no key)
  local url="https://store.steampowered.com/api/appdetails?appids=${appid}&l=en&cc=us"
  http_get "$url" || true
}

extract_requirements_and_platforms() {
  # Input: JSON from appdetails; Output: TSV of fields
  # Fields: success, linux, windows, mac, min_text, rec_text, type
  local appid="$1" json="$2"
  # Some apps return {"APPID": {"success":true, "data":{...}}}
  local out
  out=$(jq -r --arg APP "$appid" '
		.[$APP] as $root | if ($root.success==true and ($root.data|type)=="object") then
			($root.data.platforms.linux // false) as $linux |
			($root.data.platforms.windows // false) as $windows |
			($root.data.platforms.mac // false) as $mac |
			($root.data.type // "") as $type |
			# Prefer Linux reqs when present
			($root.data.linux_requirements.minimum // $root.data.pc_requirements.minimum // "") as $min |
			($root.data.linux_requirements.recommended // $root.data.pc_requirements.recommended // "") as $rec |
			["ok", ($linux|tostring), ($windows|tostring), ($mac|tostring), ($min|tostring), ($rec|tostring), ($type|tostring)] | @tsv
		else
			["fail", "false", "false", "false", "", "", ""] | @tsv
		end' 2> /dev/null <<< "$json") || true
  if [[ -z $out ]]; then
    out=$'fail	false	false	false			'
  fi
  printf '%s\n' "$out"
}

# Read JSON from stdin (avoids storing large/binary data in variables)
extract_requirements_and_platforms_stdin() {
  local appid="$1"
  local out
  out=$(jq -r --arg APP "$appid" '
		.[$APP] as $root | if ($root.success==true and ($root.data|type)=="object") then
			($root.data.platforms.linux // false) as $linux |
			($root.data.platforms.windows // false) as $windows |
			($root.data.platforms.mac // false) as $mac |
			($root.data.type // "") as $type |
			($root.data.linux_requirements.minimum // $root.data.pc_requirements.minimum // "") as $min |
			($root.data.linux_requirements.recommended // $root.data.pc_requirements.recommended // "") as $rec |
			["ok", ($linux|tostring), ($windows|tostring), ($mac|tostring), ($min|tostring), ($rec|tostring), ($type|tostring)] | @tsv
		else
			["fail", "false", "false", "false", "", "", ""] | @tsv
		end' 2> /dev/null) || true
  if [[ -z $out ]]; then
    out=$'fail\tfalse\tfalse\tfalse\t\t\t'
  fi
  printf '%s\n' "$out"
}

fetch_protondb_tier() {
  local appid="$1"
  local url="https://www.protondb.com/api/v1/reports/summaries/${appid}.json"
  # Returns minimal JSON including .tier, .confidence; we only need .tier
  local tier
  tier=$(http_get "$url" | jq -r 'try .tier // "unknown"' 2> /dev/null || true)
  if [[ -z $tier || $tier == "null" ]]; then
    echo "unknown"
  else
    tr '[:upper:]' '[:lower:]' <<< "$tier" | tr -d '\r\n'
  fi
}

protondb_allowed() {
  local tier
  tier=$(tr '[:upper:]' '[:lower:]' <<< "${1:-}")
  case "$tier" in
    platinum | native | gold | silver | unknown | "") return 0 ;;
    bronze | pending | borked | unsupported | broken) return 1 ;;
    *) return 0 ;;
  esac
}
