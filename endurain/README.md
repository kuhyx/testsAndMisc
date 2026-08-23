# Endurain + RunnerUp WebDAV sync

Self-hosted fitness tracker ([Endurain](https://codeberg.org/endurain-project/endurain))
fed by RunnerUp exports from the phone.

**Endurain is a viewer.** `screen-locker`'s workout gate still reads the phone
over adb and is untouched by anything here — a WebDAV drop folder is trivially
spoofable by anything that can write to `~/cloud`, so it must never become an
unlock authority.

## Paths

| What | Where |
|---|---|
| Public URL | `https://endurain.kuhy.duckdns.org` |
| Local URL | `http://127.0.0.1:8085` (loopback only) |
| WebDAV inbox | `https://kuhy-cloud.duckdns.org/RunnerUp` → `~/cloud/RunnerUp/` |
| Runtime data | `/var/opt/endurain/` |
| Ledger | `~/.local/state/endurain-import/ledger.json` |
| Importer code | `../python_pkg/endurain_import/` (repo requires Python under `python_pkg/`) |
| Secrets | `.env`, `.api_key` (both gitignored, mode 600) |

## Flow

```
phone --(WebDAV, manual tap)--> dufs ~/cloud/RunnerUp/ --\
                                                          >-- importer --> Endurain
phone --(adb pull, fallback)--> ~/cloud/RunnerUp/ -------/
```

A systemd user timer (`endurain-import.timer`) runs every 15 min.

## Commands

```bash
./scripts/setup_endurain.sh          # provision / restart the stack
./scripts/publish_endurain.sh        # install the Caddy site (gated)
systemctl --user start endurain-import.service   # import now
journalctl --user -u endurain-import.service -n 30
cd .. && .venv/bin/python -m pytest python_pkg/endurain_import/tests/ -q  # 52 tests
```

## Things that will bite you

- **RunnerUp has no background sync.** No `WorkManager`, `JobScheduler` or
  `AlarmManager` anywhere in its source. Every upload is a manual tap on the
  save/upload button after a run. This is not configurable.
- **The WebDAV URL must not end in a slash.** RunnerUp builds the target as
  `url + fileBase + fileExt` where `fileBase` already starts with `/`.
- **`MKCOL` is not supported by dufs.** RunnerUp `PROPFIND`s the directory and
  only issues `MKCOL` on 404, so `~/cloud/RunnerUp/` must exist on disk or
  adding the account fails with an opaque generic error (upstream #1147/#1172).
- **HTTPS is mandatory.** RunnerUp targets `targetSdk 36` with no
  `usesCleartextTraffic`, so Android blocks plain HTTP. Self-signed certs are
  broken upstream (stock `OkHttpClient`, system trust store only) — this is why
  it rides on the existing Let's Encrypt cert.
- **Endurain does not deduplicate.** Re-uploading a file creates a second
  activity. All dedupe is the importer's job, on two axes: the content hash,
  *and* an activity key that collapses the `.gpx`/`.tcx` pair RunnerUp writes
  for a single run (different bytes, same run).
- **`X-API-Key`, not `X-Client-Type`.** Endurain's own OpenAPI schema declares
  the `APIKeyHeader` scheme with the wrong name; verified against the server.
- **postgres:18 moved `PGDATA`** to `/var/lib/postgresql/18/docker`. Upstream's
  compose example still mounts the pre-18 path, which fails as an unexplained
  "container is unhealthy".
- **The admin account is seeded `admin`/`admin`** by an Alembic migration with
  no env override. `publish_endurain.sh` refuses to expose the service until
  that password is changed.
