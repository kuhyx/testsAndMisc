#!/bin/bash
# Merge all KeePassXC database files in a directory into a single database
# Merges databases one by one, deleting the source after each successful merge
# until only ONE database remains.
#
# IMPORTANT: You will be prompted for the master password for each database!
# Make sure all databases use the same master password, or know each password.
#
# Usage: ./sync_keepassxc.sh [directory]
# Default directory: ~/Keepass

set -euo pipefail

# Source common library if available
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
if [[ -f "$SCRIPT_DIR/../lib/common.sh" ]]; then
	# shellcheck source=../lib/common.sh
	source "$SCRIPT_DIR/../lib/common.sh"
else
	log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fi

# Configuration
KEEPASS_DIR="${1:-$HOME/Keepass}"
BACKUP_DIR="$KEEPASS_DIR/.backup_$(date +%Y%m%d_%H%M%S)"

# Ensure keepassxc-cli is installed
if ! command -v keepassxc-cli &>/dev/null; then
	log "ERROR: 'keepassxc-cli' is not installed. Install with: sudo pacman -S keepassxc"
	exit 1
fi

# Check if directory exists
if [[ ! -d "$KEEPASS_DIR" ]]; then
	log "ERROR: Directory does not exist: $KEEPASS_DIR"
	exit 1
fi

# Find all .kdbx files
mapfile -t KDBX_FILES < <(find "$KEEPASS_DIR" -maxdepth 1 -name "*.kdbx" -type f | sort)

if [[ ${#KDBX_FILES[@]} -eq 0 ]]; then
	log "No .kdbx files found in $KEEPASS_DIR"
	exit 0
fi

if [[ ${#KDBX_FILES[@]} -eq 1 ]]; then
	log "Only one .kdbx file found. Nothing to merge."
	log "File: ${KDBX_FILES[0]}"
	exit 0
fi

log "Found ${#KDBX_FILES[@]} .kdbx files in $KEEPASS_DIR:"
for f in "${KDBX_FILES[@]}"; do
	echo "  - $(basename "$f")"
done

# Create backup directory
mkdir -p "$BACKUP_DIR"
log "Creating backups in: $BACKUP_DIR"

# Backup all files before any operation
for f in "${KDBX_FILES[@]}"; do
	cp -v "$f" "$BACKUP_DIR/"
done
log "All files backed up successfully."

echo ""
echo "=============================================="
echo "WARNING: This will merge all databases into ONE"
echo "and DELETE the source files after each merge."
echo ""
echo "Backups are stored in: $BACKUP_DIR"
echo "=============================================="
echo ""
read -rp "Do you want to continue? (yes/no): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
	log "Aborted by user."
	exit 1
fi

# Select the target database (the one to merge INTO)
# We'll use the first one alphabetically, or you could let user choose
TARGET_DB="${KDBX_FILES[0]}"
log "Target database (will contain all merged data): $(basename "$TARGET_DB")"

echo ""
echo "You will need to enter the master password for the databases."
echo ""

# Read target database password
read -rsp "Enter master password for TARGET database ($(basename "$TARGET_DB")): " TARGET_PASSWORD
echo ""

# Verify target password works
if ! echo "$TARGET_PASSWORD" | keepassxc-cli ls "$TARGET_DB" &>/dev/null; then
	log "ERROR: Failed to open target database. Wrong password?"
	exit 1
fi
log "Target database password verified."

# Ask if all databases share the same password
echo ""
read -rp "Do ALL databases share the same master password? (y/n): " SAME_PASSWORD
SAME_PASSWORD="${SAME_PASSWORD,,}" # lowercase

# Merge each source database into the target
MERGE_COUNT=0
for ((i = 1; i < ${#KDBX_FILES[@]}; i++)); do
	SOURCE_DB="${KDBX_FILES[$i]}"
	log ""
	log "Merging $(basename "$SOURCE_DB") into $(basename "$TARGET_DB")..."

	# Reuse target password if user confirmed all are the same
	if [[ "$SAME_PASSWORD" == "y" || "$SAME_PASSWORD" == "yes" ]]; then
		SOURCE_PASSWORD="$TARGET_PASSWORD"
	else
		# Ask for source password (might be different)
		echo ""
		read -rsp "Enter master password for SOURCE database ($(basename "$SOURCE_DB")): " SOURCE_PASSWORD
		echo ""
	fi

	# Verify source password
	if ! echo "$SOURCE_PASSWORD" | keepassxc-cli ls "$SOURCE_DB" &>/dev/null; then
		log "ERROR: Failed to open source database $(basename "$SOURCE_DB"). Wrong password?"
		log "Skipping this database. You can try again later."
		continue
	fi

	# Perform the merge
	# keepassxc-cli merge requires: target_db source_db
	# It will prompt for passwords
	if echo -e "${TARGET_PASSWORD}\n${SOURCE_PASSWORD}" | keepassxc-cli merge "$TARGET_DB" "$SOURCE_DB"; then
		log "Successfully merged $(basename "$SOURCE_DB")"

		# Delete the source database after successful merge
		log "Deleting source database: $(basename "$SOURCE_DB")"
		rm -v "$SOURCE_DB"
		((MERGE_COUNT++)) || true
	else
		log "ERROR: Failed to merge $(basename "$SOURCE_DB")"
		log "Source database NOT deleted. Check the backup and try manually."
	fi
done

echo ""
log "=============================================="
log "Merge complete!"
log "Merged $MERGE_COUNT database(s) into: $(basename "$TARGET_DB")"
log "Backups are preserved in: $BACKUP_DIR"
log "=============================================="

# Show final state
log ""
log "Remaining .kdbx files in $KEEPASS_DIR:"
find "$KEEPASS_DIR" -maxdepth 1 -name "*.kdbx" -type f -exec basename {} \;

# Rename to clean name if desired
FINAL_COUNT=$(find "$KEEPASS_DIR" -maxdepth 1 -name "*.kdbx" -type f | wc -l)
if [[ $FINAL_COUNT -eq 1 ]]; then
	log ""
	FINAL_NAME="$KEEPASS_DIR/Passwords.kdbx"
	if [[ "$TARGET_DB" != "$FINAL_NAME" ]]; then
		read -rp "Rename final database to 'Passwords.kdbx'? (y/n): " RENAME_CONFIRM
		if [[ "$RENAME_CONFIRM" == "y" ]]; then
			mv -v "$TARGET_DB" "$FINAL_NAME"
			log "Final database: $FINAL_NAME"
		fi
	fi
	log ""
	log "SUCCESS: You now have exactly ONE KeePassXC database!"
fi
