# Horatio — Script Memorization App Design Spec

## Overview

**Horatio** is a multiplatform app (iOS, Android, Windows, Linux, macOS) for actors
to learn their scripts through structured rehearsal and spaced repetition.

Named after Hamlet's loyal friend — the faithful companion who helps you remember.

## Architecture

**Two-package monorepo managed by Melos:**

- `horatio_core` — Pure Dart package: script parsing, models, SM-2 SRS, memorization planner
- `horatio_app` — Flutter app: UI, TTS, audio, Bloc/Cubit state management, drift database

## Tech Stack

- **Framework:** Flutter 3.x (Dart 3.x)
- **State management:** Bloc/Cubit
- **Database:** SQLite via drift (type-safe, reactive, migrations)
- **TTS:** System TTS via flutter_tts (offline)
- **Monorepo:** Melos
- **Lint:** Strictest possible dart analysis + DCM + pre-commit hooks

## Core Models

- `Script` — Full parsed document (title, scenes, roles, lines)
- `Role` — Character name + all their lines
- `ScriptLine` — Text content, role, scene index, position, optional stage direction
- `Scene` — Ordered list of lines with scene title
- `SrsCard` — Line/cue pair with SM-2 data (interval, ease factor, next review date)
- `RehearsalSession` — Progress through a dialogue sequence

## Screen Flow

1. **Home** — Imported scripts list + public domain library + import button
2. **Import** — File picker for PDF/DOCX/TXT/ODS, parsing progress
3. **Role Selection** — Detected roles with line counts, deadline picker
4. **Schedule Overview** — Calendar of daily memorization sessions
5. **Dialogue Rehearsal** — TTS reads others' lines, actor types their response
6. **SRS Review** — Flashcard interface with SM-2 scheduling

## Script Parsing

**Supported formats:** TXT, PDF, DOCX, ODS

**Role detection heuristics (priority order):**

1. Screenplay format: `CHARACTER NAME` in ALL CAPS on its own line
2. Colon format: `CHARACTER: dialogue text`
3. Parenthetical: `CHARACTER (stage direction) dialogue`
4. Bracketed: `[CHARACTER] dialogue`

**Edge cases:** Stage directions preserved but not treated as dialogue. Cross-page
line merging. Narration tagged as STAGE_DIRECTION.

## SM-2 Spaced Repetition

Standard SM-2 algorithm:

- Each line/cue pair becomes an SRS card
- New cards introduced per deadline schedule
- Review intervals adjusted by ease factor (1.3 minimum)
- Long monologues split into sentence-pair cards

## Dialogue Rehearsal Mode

- Sequential scene playback
- Other characters' lines read by TTS
- Actor types their line at each cue
- Levenshtein distance for fuzzy matching
- Diff highlighting for feedback
- Session progress feeds into SRS scheduling

## Public Domain Library

Pre-parsed scripts bundled as JSON assets:

- Shakespeare: Hamlet, Romeo and Juliet, Macbeth, A Midsummer Night's Dream,
  Othello, The Tempest
- Chekhov: The Cherry Orchard, Three Sisters, The Seagull, Uncle Vanya
- Molière: Tartuffe, The Misanthrope
- Oscar Wilde: The Importance of Being Earnest
- Ibsen: A Doll's House, Hedda Gabler

## Code Quality

- Strictest dart analysis (strict-casts, strict-inference, strict-raw-types)
- 50+ lint rules enabled
- dart_code_metrics for complexity limits
- Pre-commit hooks: analyze, format, test
- Coverage: 100% on core, 90%+ on app
- Melos for consistent cross-package commands

## MVP Phases

**Phase 1 (MVP):** Import, role detection, rehearsal mode, SRS cards, schedule
**Phase 2:** Audio recording, performance notes, stress annotations, public domain browser
