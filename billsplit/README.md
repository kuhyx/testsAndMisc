# BillSplit

Flutter app (mobile + desktop) for splitting shop receipts between people —
including the drinkers vs non-drinkers case — with Biedronka e-paragon import
and .xlsx export.

## Features

- **People roster** with a per-person _drinks alcohol_ toggle, plus arbitrary
  **groups** (tags) like "meat eaters".
- **Receipts**: import a Polish fiscal e-receipt JSON (`e-paragon`,
  JPK_KASA_PARAGON_v2-0 — the file the Biedronka app exports; the embedded JWS
  payload is decoded, signature not verified) or build one manually. Multiple
  receipts persist locally (`state.json` in app documents).
- **Per-item assignment**: each item is split among _Everyone / Drinkers /
  Non-drinkers / a group / hand-picked people_. Alcohol is auto-detected on
  import (wódka/piwo/wino/… keywords) and defaults to drinkers only; deposits
  (kaucja) become their own line split among everyone. Category and assignment
  are always editable — the keyword detection is a default, not a decision.
- **Grosz-exact math**: every item's shares sum to exactly the item total
  (largest-remainder distribution), so per-person totals reconcile with the
  receipt to the grosz — no floating point drift.
- **Totals view**: per person, with alcohol / rest breakdown, unassigned-item
  warnings, and a reconciliation check against the paid amount.
- **Export .xlsx**: one row per item with a 1/0 person matrix plus a summary —
  same layout as the hand-made spreadsheet this app grew out of. Matrix and
  summary are exported values (the app is the calculator); column totals are
  live SUM formulas.

## Running

The repo ships `lib/`, `test/`, and `pubspec.yaml` without platform runner
folders. Generate them once for the platforms you want:

```sh
cd billsplit
flutter create . --platforms=linux,windows,macos,android,ios
flutter pub get
flutter run          # picks a connected device / desktop
```

Tested with Flutter 3.44.8 / Dart 3.10.

## Tests

```sh
flutter test
```

Covers: parsing the real sample receipt in `test/fixtures/` (49 items +
deposit, totals 590.55 + 7.00 = 597.55 zł), split invariants incl. a 500-case
fuzz of the remainder distribution, assignment-mode resolution, and xlsx
generation (the test writes `build/test_export.xlsx` for external inspection).

## Design notes / edge cases

- Money is `int` grosze end to end; formatting happens only at the UI edge.
- An item resolving to zero people (e.g. "non-drinkers" on an all-drinker
  receipt) is **excluded from totals and loudly flagged**, never silently
  dropped into someone's bill.
- Deleting a person prunes them from groups, receipt participants and custom
  assignments; deleting a group falls back affected items to _Everyone_.
- Assignment modes are stored symbolically (not as materialized ID sets), so
  adding a person later automatically includes them in _Everyone_ items.
  Touching a person checkbox materializes the current set and switches the
  item to _custom_.
- `paidTotalGr` (what the card was charged) is kept separately from the item
  sum; a mismatch shows red in Totals instead of being "fixed" silently.

## Quality gates (enforced in CI)

- `dart format --set-exit-if-changed .` — formatting is canonical
- `flutter analyze --fatal-infos` — `very_good_analysis` + `strict-casts`,
  `strict-inference`, `strict-raw-types`; any info fails the build
- `flutter test --coverage` + `tool/coverage_check.py` — **100% line
  coverage of `lib/` is mandatory**; the gate also fails if a lib file is
  never executed by any test
