#!/bin/bash
# Migrate all of kuhyx's GitHub repos to the self-hosted Gitea instance
# (see setup_gitea.sh) as pull-mirrors, so Gitea keeps them in sync on its
# own -- this single migration mechanism covers both the initial import and
# ongoing sync, no separate push step or webhook needed.
#
# Safely re-runnable: skips repos that already exist on Gitea, so re-running
# later also picks up any new GitHub repos for free.
#
# Scope: only non-fork repos owned by kuhyx (21 at last count, 5 private).
# Local-only repos with no GitHub remote (e.g. ~/guard-lib) are out of scope.
#
# Private-repo credential: a dedicated fine-grained GitHub PAT (Contents:
# Read-only, scoped to just these repos), NOT the broad-scope `gh auth token`
# -- this host is internet-facing, so the mirror credential stored in
# Gitea's config should carry the least privilege that works. Public repos
# need no credential at all and clone anonymously.
#
# Usage: ./migrate_github_to_gitea.sh

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

readonly GITEA_DOMAIN="kuhy.duckdns.org"
readonly GITEA_OWNER="kuhyx"
readonly GITHUB_OWNER="kuhyx"
readonly GITEA_TOKEN_FILE="${HOME}/gitea/.admin_token"
readonly GITHUB_MIRROR_TOKEN_FILE="${HOME}/gitea/.github_mirror_token"

die() {
	log_error "$1"
	exit 1
}

require_command gh || die "gh CLI is required."
require_command curl || die "curl is required."
[[ -f $GITEA_TOKEN_FILE ]] || die "No Gitea API token at ${GITEA_TOKEN_FILE} -- run setup_gitea.sh first."
[[ -f $GITHUB_MIRROR_TOKEN_FILE ]] || die "No GitHub mirror PAT at ${GITHUB_MIRROR_TOKEN_FILE} -- create a fine-grained PAT (Contents: Read-only) and save it there (chmod 600) first."

GITEA_TOKEN="$(cat "$GITEA_TOKEN_FILE")"
readonly GITEA_TOKEN
GITHUB_MIRROR_TOKEN="$(cat "$GITHUB_MIRROR_TOKEN_FILE")"
readonly GITHUB_MIRROR_TOKEN

repo_exists_on_gitea() {
	local name="$1" status
	status=$(curl -s -o /dev/null -w '%{http_code}' \
		-H "Authorization: token ${GITEA_TOKEN}" \
		"https://${GITEA_DOMAIN}/api/v1/repos/${GITEA_OWNER}/${name}")
	[[ $status == "200" ]]
}

migrate_repo() {
	local name="$1" is_private="$2"
	local auth_field="" payload response http_code body
	if [[ $is_private == "true" ]]; then
		auth_field="\"auth_token\": \"${GITHUB_MIRROR_TOKEN}\","
	fi
	payload=$(
		cat <<JSON
{
	"clone_addr": "https://github.com/${GITHUB_OWNER}/${name}.git",
	"repo_name": "${name}",
	"repo_owner": "${GITEA_OWNER}",
	"private": ${is_private},
	"mirror": true,
	"mirror_interval": "10m0s",
	${auth_field}
	"wiki": true,
	"issues": false,
	"pull_requests": false,
	"releases": true
}
JSON
	)
	response=$(curl -s -w '\n%{http_code}' -X POST "https://${GITEA_DOMAIN}/api/v1/repos/migrate" \
		-H "Authorization: token ${GITEA_TOKEN}" -H "Content-Type: application/json" \
		-d "$payload")
	http_code="${response##*$'\n'}"
	body="${response%$'\n'*}"
	if [[ $http_code == "201" ]]; then
		log_ok "Migrated ${name} (private=${is_private})."
	else
		log_error "Failed to migrate ${name} (HTTP ${http_code}): ${body}"
		return 1
	fi
}

main() {
	log_info "Enumerating non-fork GitHub repos owned by ${GITHUB_OWNER}..."
	local failures=0 total=0 skipped=0 migrated=0
	while IFS=$'\t' read -r name is_private; do
		[[ -n $name ]] || continue
		total=$((total + 1))
		if repo_exists_on_gitea "$name"; then
			log_info "Skipping ${name} -- already exists on Gitea."
			skipped=$((skipped + 1))
			continue
		fi
		if migrate_repo "$name" "$is_private"; then
			migrated=$((migrated + 1))
		else
			failures=$((failures + 1))
		fi
	done < <(gh repo list "$GITHUB_OWNER" --limit 200 --json name,isPrivate,isFork \
		--jq '.[] | select(.isFork==false) | [.name, .isPrivate] | @tsv')

	log_ok "Done: ${total} repos considered, ${migrated} migrated, ${skipped} already present, ${failures} failed."
	[[ $failures -eq 0 ]] || exit 1
}

main "$@"
