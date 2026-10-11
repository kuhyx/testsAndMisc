#!/usr/bin/env bash
#
# Scaled Krita launcher (shadows /usr/bin/krita on PATH).
#   QT_SCALE_FACTOR=2  -> whole GUI at 2x (crisp, image res & tablet unaffected)
#   XCURSOR_SIZE=32    -> ~2.5x on-screen cursor (visual only, no stroke change)
# Tune the two numbers to taste. exec keeps the same PID/args.
#
exec env QT_SCALE_FACTOR=2 XCURSOR_SIZE=32 /usr/bin/krita "$@"
