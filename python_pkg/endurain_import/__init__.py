"""RunnerUp -> Endurain importer.

Moves RunnerUp activity exports into Endurain exactly once, from two sources:

  1. the WebDAV inbox the phone uploads to (primary), and
  2. ``adb pull`` from the phone's RunnerUp export dir (fallback).

Endurain performs no duplicate detection of its own -- re-importing a file
creates a second activity -- so deduplication is entirely this package's
responsibility. See :mod:`ledger`.
"""
