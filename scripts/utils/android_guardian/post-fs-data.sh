#!/system/bin/sh
# Runs early in boot - set up hosts file
# MODDIR is set by Magisk and points to this module's directory
GUARDIAN_DIR="/data/adb/android_guardian"

mkdir -p "$GUARDIAN_DIR"

# Log that we're starting
echo "[$(date '+%Y-%m-%d %H:%M:%S')] post-fs-data: Guardian module loading" >>"$GUARDIAN_DIR/guardian.log"
