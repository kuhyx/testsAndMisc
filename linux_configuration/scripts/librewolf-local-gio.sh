#!/usr/bin/env bash
#
# LibreWolf launcher (shadows /usr/bin/librewolf on PATH).
#   GIO_USE_VFS=local -> GIO skips gvfs entirely. Right after login gvfs's
#   D-Bus calls can hang for the 25 s D-Bus timeout each; LibreWolf made ~9 of
#   them serially and took ~4 min to open (2026-11-01). Cost: GTK dialogs lose
#   gvfs URIs (smb://, sftp://), which LibreWolf never needed.
#
exec env GIO_USE_VFS=local /usr/bin/librewolf "$@"
