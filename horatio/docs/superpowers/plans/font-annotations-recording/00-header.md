nbbbfv# Font Scaling, Word-Level Marks, Voice Recording & Note UX — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Horatio app usable on 4K displays with auto-responsive font scaling + manual control, replace whole-line marks with word-level text selection, add per-line voice recording with playback and grading, and improve note UX with inline chips and edit/delete.

**Architecture:** Incremental feature layering on the existing Drift + flutter_bloc stack. Each chunk builds on the previous: font scaling is independent, word-level marks replace the existing long-press flow, recording adds a new data layer (model → table → DAO → service → cubit → UI), note UX enhances existing cubit/DAO/widgets.

**Tech Stack:** Flutter 3.10+, Dart 3.11+, flutter_bloc, Drift (SQLite), shared_preferences, audioplayers ^6.1.0, record ^6.2.0 (already in pubspec), mocktail, bloc_test

**Spec:** `docs/superpowers/specs/2026-03-29-font-annotations-recording-design.md`

**Pipeline:** `./run.sh test` runs analyze + codegen + test with 100% branch coverage. `.g.dart` and `tables/` files are filtered from coverage.

---

## File Structure

### New Files

| File                                                           | Responsibility                                                |
| -------------------------------------------------------------- | ------------------------------------------------------------- |
| `horatio_app/lib/bloc/text_scale/text_scale_cubit.dart`        | Text scale factor management + SharedPreferences persistence  |
| `horatio_app/lib/bloc/text_scale/text_scale_state.dart`        | Equatable state for TextScaleCubit                            |
| `horatio_app/lib/widgets/text_scale_settings_sheet.dart`       | Bottom sheet with slider 0.5–3.0x + reset button              |
| `horatio_app/test/bloc/text_scale_cubit_test.dart`             | Unit tests for TextScaleCubit                                 |
| `horatio_app/test/widgets/text_scale_settings_sheet_test.dart` | Widget tests for settings sheet                               |
| `horatio_app/lib/widgets/mark_selection_toolbar.dart`          | Floating toolbar with 6 colored chips for mark type selection |
| `horatio_app/test/widgets/mark_selection_toolbar_test.dart`    | Widget tests for toolbar                                      |
| `horatio_core/lib/src/models/line_recording.dart`              | Immutable model for voice recordings                          |
| `horatio_core/test/models/line_recording_test.dart`            | JSON round-trip + equality tests                              |
| `horatio_app/lib/database/tables/line_recordings_table.dart`   | Drift table definition                                        |
| `horatio_app/lib/database/daos/recording_dao.dart`             | CRUD DAO for recordings                                       |
| `horatio_app/test/database/recording_dao_test.dart`            | Integration tests for RecordingDao                            |
| `horatio_app/lib/services/recording_service.dart`              | Wraps `record` package for mic capture                        |
| `horatio_app/lib/services/audio_playback_service.dart`         | Wraps `audioplayers` for playback                             |
| `horatio_app/test/services/recording_service_test.dart`        | Mock-based unit tests                                         |
| `horatio_app/test/services/audio_playback_service_test.dart`   | Mock-based unit tests                                         |
| `horatio_app/lib/bloc/recording/recording_cubit.dart`          | State machine for record/play/grade lifecycle                 |
| `horatio_app/lib/bloc/recording/recording_state.dart`          | Recording state hierarchy                                     |
| `horatio_app/test/bloc/recording_cubit_test.dart`              | Full branch coverage cubit tests                              |
| `horatio_app/lib/widgets/grade_stars.dart`                     | 0–5 star grading widget                                       |
| `horatio_app/lib/widgets/recording_action_bar.dart`            | Record/Play/Grade bottom bar                                  |
| `horatio_app/lib/widgets/recording_badge.dart`                 | Mic icon + count badge per line                               |
| `horatio_app/lib/widgets/recording_list_sheet.dart`            | Bottom sheet listing all recordings for a line                |
| `horatio_app/lib/widgets/note_chip.dart`                       | Tappable inline note chip                                     |
| `horatio_app/test/widgets/grade_stars_test.dart`               | Widget tests                                                  |
| `horatio_app/test/widgets/recording_action_bar_test.dart`      | Widget tests                                                  |
| `horatio_app/test/widgets/recording_badge_test.dart`           | Widget tests                                                  |
| `horatio_app/test/widgets/recording_list_sheet_test.dart`      | Widget tests                                                  |
| `horatio_app/test/widgets/note_chip_test.dart`                 | Widget tests                                                  |

### Modified Files

| File                                                          | Changes                                                                       |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `horatio_app/pubspec.yaml`                                    | Add `shared_preferences ^2.3.0`, `audioplayers ^6.1.0`                        |
| `horatio_core/lib/src/models/models.dart`                     | Export `line_recording.dart`                                                  |
| `horatio_app/lib/database/app_database.dart`                  | Add LineRecordingsTable, bump schema v1→v2, add MigrationStrategy             |
| `horatio_app/lib/database/daos/annotation_dao.dart`           | Add `updateNoteCategory` method                                               |
| `horatio_app/lib/bloc/annotation/annotation_cubit.dart`       | Change `updateNote` to accept optional category                               |
| `horatio_app/lib/app.dart`                                    | Add TextScaleCubit, RecordingDao, services to providers; wrap with MediaQuery |
| `horatio_app/lib/main.dart`                                   | Init SharedPreferences, pass to TextScaleCubit                                |
| `horatio_app/lib/screens/annotation_editor_screen.dart`       | Word selection, recording UI, note chips, settings icon                       |
| `horatio_app/lib/screens/home_screen.dart`                    | Add settings icon to AppBar                                                   |
| `horatio_app/lib/widgets/note_editor_sheet.dart`              | Add `noteId` parameter for edit mode                                          |
| `horatio_app/test/bloc/annotation_cubit_test.dart`            | Tests for updated updateNote                                                  |
| `horatio_app/test/screens/annotation_editor_screen_test.dart` | Tests for new interactions                                                    |
| `horatio_app/test/app_test.dart`                              | Update for new providers                                                      |
| `horatio_app/test/helpers/test_database.dart`                 | No changes needed (in-memory DB auto-migrates)                                |

---
