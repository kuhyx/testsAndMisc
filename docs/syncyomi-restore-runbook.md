# SyncYomi / TachiyomiSY restore runbook

Written after the 2026-08-09 incident, in which a restore that reported success
replaced a 2182-manga library with a 267 KB stub.

## The bug

TachiyomiSY **1.13.2** (current release as of 2026-08-09) fails a backup restore
with:

```
android.database.SQLException: Error code: 5, message: database is locked
```

The locked database is **the app's own `data.db` on the phone**, not the
SyncYomi server. The stack runs through Room's `InvalidationTracker` — UI
screens hold observer queries while the restore wants an exclusive write, and
the bundled SQLite returns `SQLITE_BUSY` instead of waiting.

Upstream, open and unfixed: [#1634] and [#1638].

[#1634]: https://github.com/jobobby04/TachiyomiSY/issues/1634
[#1638]: https://github.com/jobobby04/TachiyomiSY/issues/1638

## Why it is dangerous

The loud failure is survivable. The dangerous case is the quiet one:

1. A restore fails with code 5. The library is now empty or partial.
2. A retry reports `Worker result SUCCESS` — but writes almost nothing.
3. SyncYomi pushes that near-empty library to the server.
4. The good server copy is gone.

On 2026-08-09 the whole sequence took 51 seconds, and the real library survived
only as stale pages in the server's SQLite write-ahead log.

**A success toast is not evidence.** Verify by entry count, always.

## Restoring safely

1. **Turn sync OFF in SY first.** Settings → Data and storage → Sync.
   Skipping this lets a background sync overwrite the server mid-recovery.
2. **Force-stop the app** — `adb shell am force-stop eu.kanade.tachiyomi.sy`,
   or Settings → Apps → Force stop.
3. **Cold-start straight into the restore.** Do not open the library, do not
   let it sit on a tab loading covers. Every open screen is another observer
   holding a connection, which is what the restore loses the race to.
4. **Put the phone down while it runs.** Navigating during a restore adds
   exactly the contention that triggers the bug.
5. **Verify by count**, not by the toast. Compare against the guard's baseline:
   `cat ~/.local/share/syncyomi_guard/last_known_good.json`
6. **Only then re-enable sync**, so the verified library propagates up.

If it fails, force-stop and retry from step 3. Upstream reporters needed up to
five attempts. Retrying is expected, not a sign of a new problem.

If it will not restore at all, the upstream workaround is a downgrade:
install 1.12.0 → restore → upgrade back to 1.13.2. This wipes `data.db`, so do
it **only** with a verified-good `.tachibk` in hand.

## Known collateral: categories

A restore that recovers every manga can still drop **all categories and all
category memberships**. Observed 2026-08-09: 2182/2182 manga and 57 389/57 389
distinct chapters restored, while 18 categories and 1724 manga-to-category
assignments were lost. Matches the upstream report in [#1634].

Categories are not recoverable by re-syncing — the server copy is whatever the
phone last pushed. They come back only from a `.tachibk` that still has them.

## Chapter counts shrink legitimately

A restore **deduplicates** chapter entries. On 2026-08-09 the total fell from
75 376 to 68 418 (−9.2 %) while the distinct chapter count was unchanged at
57 389: 6958 duplicates were collapsed, and nothing was lost.

Do not read a falling chapter count as data loss without comparing _distinct_
chapter URLs. The guard's 10 % threshold is set above this specific event for
exactly that reason.

## The guard

`python_pkg/syncyomi_guard/` checks the server payload every 30 minutes, fails
loudly on a collapse, and keeps 14 restorable `.tachibk` snapshots.

```bash
# check now
python3 -m python_pkg.syncyomi_guard          # exit 0 healthy, 1 collapsed

# install / remove the timer
./linux_configuration/features/setup_syncyomi_guard.sh
./linux_configuration/features/setup_syncyomi_guard.sh --uninstall

systemctl --user list-timers syncyomi-guard.timer
journalctl --user -u syncyomi-guard.service -n 20
```

Snapshots live in `~/syncyomi/snapshots/` and are ordinary `.tachibk` files —
`adb push` one to the phone and restore it directly.

**Retention: 14 snapshots at 30-minute intervals is about 7 hours of history.**
That covers a fast incident — the 2026-08-09 window was 51 seconds — but not a
slow drift noticed days later. For that, the reference copy is
`~/syncyomi/recovery/`, which is never pruned.

After a **deliberate** library purge the guard will report a collapse; accept
the new state with `--accept` to re-baseline.

### Outcome of the 2026-08-09 incident

Manga and chapters were fully recovered. **The 18 categories were not, and the
loss was accepted deliberately** — the baseline now records 1 category, so the
guard runs green against reality.

Three attempts failed to get categories back onto the phone:

1. Restore the recovered `.tachibk` → app briefly showed categories, but the
   next sync pushed **1** category up.
2. `PUT` the full 18-category payload straight to the server → server held 18,
   phone synced and flattened it back to 1.
3. Repeat of 2 with the same result.

Round 2 is the informative one: the server had **18** and the phone had **1**,
and 1 won. The phone was not losing a merge — it was honestly reporting what it
had. The restore writes manga and chapters but silently drops the category
tables, which is the narrow form of the same 1.13.2 bug.

The categories still exist in `~/syncyomi/recovery/syncyomi_recovered_2026-08-09.tachibk`
(18 definitions, 1724 memberships). Getting them into the app needs the
downgrade path — 1.12.0 → restore → verify → upgrade — which was not attempted.
If a future SY release fixes #1634, retry the restore before the downgrade.

## Recovering from the server WAL (last resort)

If the server payload is already degraded and no snapshot predates it, the old
payload may still exist as stale pages in `syncyomi.db-wal`.

**Do not restart the container and do not checkpoint** — a clean close deletes
the WAL and the only remaining copy with it. Snapshot all three files first:

```bash
sudo cp -a ~/syncyomi/config/syncyomi.db{,-shm,-wal} /some/safe/dir/
```

Then rebuild by applying every WAL frame over the base database, last writer
wins, and extract `sync_data.data`. The 2026-08-09 reconstruction and its
verification are recorded in
`docs/superpowers/evidence/syncyomi-library-recovery-2026-08-09.json`.

**`~/syncyomi/recovery/recovered.db` is a forensic artifact, not a database.**
It was assembled by splicing pages from several checkpoint generations, so it is
not any single committed SQLite state — `quick_check` passes and the payload
blob decodes, but do **not** copy it over `config/syncyomi.db`. The deliverable
from that recovery is the `.tachibk` beside it.
