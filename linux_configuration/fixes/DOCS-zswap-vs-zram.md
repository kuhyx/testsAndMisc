# zswap vs zram: A/B test

**Result: zram stays.** It won in the VM and on the host by the agreed
rule, and the host still boots with it.

The curiousbits author moved from zram to zswap (citing Chris Down and Hayden
James). This PC ran `setup_zram.sh`: a 32 GiB zstd zram device at priority
100 above two disk swapfiles at -1, swappiness 100, zswap off. With that
order a cold page never leaves zram for disk. This file records a seeded
benchmark of both setups, in a vmbox guest and on the host, and which one
the host now boots with.

## Setups

|                | zram (`setup_zram.sh`)                                  | zswap (`setup_zswap.sh`)                                                                                     |
| -------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| kernel cmdline | `zswap.enabled=0`                                       | `zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=35 zswap.shrinker_enabled=1`                   |
| compressed RAM | `/dev/zram0`, 32 GiB uncompressed, zstd, prio 100       | zswap pool, at most 35 % of RAM, zstd, zsmalloc (the only pool on kernel 7.3, so there is no `zswap.zpool=`) |
| disk swap      | `/swapfile` 40G + `/swapfile2` 24G at -1, overflow only | same files, the backing store zswap writes cold pages to                                                     |
| cold pages     | stay in zram until it fills                             | the shrinker writes them back to disk                                                                        |
| swappiness     | 100                                                     | 100                                                                                                          |
| hibernation    | `resume=` on `/swapfile`, unchanged                     | unchanged                                                                                                    |

The 35 % cap gives both setups the same RAM budget: 32 GiB at the measured
~3.2:1 is ~10 GiB, about 35 % of the host's 30 GiB. The vmbox guest scales
its zram device the same way (`ZRAM_SIZE_MIB` = 35 % of RAM × 3.2, 4.3 GiB
on a 3.9 GiB guest).

Each script is the one-command switch to its setup, and the revert from the
other:

```bash
sudo linux_configuration/fixes/setup_zswap.sh   # exit 3 = reboot to apply
sudo linux_configuration/fixes/setup_zram.sh
```

`setup_zswap.sh` writes the cmdline first (every systemd-boot entry, or
GRUB's defaults plus `grub-mkconfig`), removes the zram-generator conf, then
switches live: swapoff zram0, then zswap on, so no page is compressed twice.
When MemAvailable cannot take back what zram holds plus 2 GiB, it leaves the
live state alone and exits 3: the next boot comes up on zswap.
`setup_zram.sh` restores `zswap.enabled=0`, reinstalls the conf, starts
zram0 and only then turns zswap off; pages still in the zswap pool drain as
they fault in. The original loader entries are kept in
`/var/lib/swap-switch/*.orig`.

## Method

`swap_bench.sh run host|vm` runs `python_pkg/swap_bench` once and appends
one row to `swap-bench-results.tsv`; `swap_bench.sh summary` prints the
medians and the winner. Every run stays under 60 s.

- **Workload.** A seeded anonymous mapping (seed 20261127): pages drawn from
  a pool of Zipf-weighted text over a 64-word seeded vocabulary plus 5 %
  random pages, about 3.2:1 under zstd. Then a seeded 25 % hot subset is
  read three times, which is where the major faults come from. No file
  contents and no clock go in, so the page count and both CRCs are the same
  on every run, host or guest (C7).
- **Host.** 6 GiB under a transient `systemd-run --user --scope` with
  `MemoryMax=4G`, `MemorySwapMax=infinity`, `RuntimeMaxSec=55`. Only the
  scope is pressed; PSI, zswap counters and writeback come from the scope's
  own `memory.pressure` and `memory.stat`. A host run refuses to start
  when MemAvailable is below the 4 GiB cap plus 2 GiB. It fails (exit 3,
  row kept) when the login sessions stalled more than 1 s during the run
  (`SWAP_BENCH_MAX_DESKTOP_MS`). (8 GiB took 37-45 s on zram with other jobs
  running; zswap is slower, so 6 GiB keeps every run inside the 50 s limit.)
- **VM.** 4.5 GiB in a 3.9 GiB guest (8 GiB swapfile), no scope: the whole
  guest is pressed and global counters are used.
- **Columns.** `ratio`: this run's stored-in over stored-out bytes (zram
  `mm_stat` deltas at peak; zswap `zswapped/zswap` at peak). `psi_*_ms`:
  memory stall time over the run. `majflt`: the workload's own major faults.
  `disk_wb_pages`: pages written to disk swap, Δ`pswpout` minus Δ zram
  writes (zram is a swap device, so `pswpout` counts it too). It is
  system-wide, so on the host it includes other processes (see the C6
  check below). `zswpwb`: zswap's writebacks. `desktop_full_ms` (host): full
  stall of the login session scopes, i.e. the desktop, during the run.
  `outside_pswpout` (host, added after the A/B rows): global Δ`pswpout`
  minus the scope's own `pswpout`, the pages every other process swapped
  out during the run. `global_full_avg10`: global PSI full after the run;
  it counts the bench scope's own stall, so it does not measure the
  desktop.
- **Winner rule** (kuhy, 2026-11-27). Lower median PSI full wins; major
  faults break a tie; a difference under 10 % (the run-to-run noise) is a
  tie, and a tie on both keeps zram.
- **Known bias.** zswap's pool is charged to the cgroup that owns the pages;
  zram's device memory is not. Under the host scope's 4 GiB cap, zswap's
  pool eats into the scope's own RAM while zram's does not, so the host
  numbers favour zram. The VM run, pressed system-wide, has no such bias.

## Results (2026-11-27, kernel 7.3.6)

Medians of 3 runs per setup, from `swap_bench.sh summary`:

### VM (vmbox, 3.9 GiB RAM, 4 vCPU, 8 GiB swapfile, 4.5 GiB workload)

| setup | runs | ratio | PSI some ms | PSI full ms | major faults | disk writeback pages | zswap writeback |
| ----- | ---- | ----- | ----------- | ----------- | ------------ | -------------------- | --------------- |
| zram  | 3    | 3.21  | 5996        | 5996        | 124816       | 0                    | 0               |
| zswap | 3    | 3.16  | 10366       | 10360       | 147757       | 92                   | 92              |

Winner: **zram**. Median PSI full is 5996 ms for zram and 10360 ms for
zswap, 42 % lower. zram's three runs span 5782-6118 ms; zswap's span
8832-12826 ms.

### Host (30 GiB, 6 GiB workload in a 4 GiB scope)

| setup | runs | ratio | PSI some ms | PSI full ms | major faults | disk writeback pages | zswap writeback |
| ----- | ---- | ----- | ----------- | ----------- | ------------ | -------------------- | --------------- |
| zram  | 3    | 2.83  | 7427        | 7427        | 172634       | 0                    | 0               |
| zswap | 3    | 3.21  | 8973        | 8973        | 218408       | 617001               | 453067          |

Winner: **zram**. Median PSI full is 7427 ms for zram and 8973 ms for zswap,
17 % lower, which is past the 10 % noise bar. The host's spread is wide,
because other board jobs (gradle, an emulator, ollama) ran during the runs:
zram 5546-8223 ms, zswap 5490-11684 ms. Major faults point the same way
(-21 %). zswap wrote 1.3-2.3 GB of this run's pages back to disk per run
(`zswpwb` 331649-586700 pages), because its pool counts against the scope's
4 GiB. zram's three A/B runs recorded no disk writeback. zram's ratio reads lower (2.8 vs 3.2)
only because `mm_stat` is device-wide, so other processes swapping during
the run dilute it. zswap's ratio comes from the scope's own counters.

### Desktop check on the host (C6, zram, re-measured in the fix stage)

The bench scope caps the bench's RAM, but it does not keep the rest of the
host out of swap. Three zram runs with the `outside_pswpout` column,
against an idle 28 s measured the same way with no bench running:

| interval | seconds | desktop full stall ms | other processes' pswpout | pswpout not taken by zram |
| -------- | ------- | --------------------- | ------------------------ | ------------------------- |
| idle     | 28      | 4                     | 110829                   | 20048                     |
| run 1    | 27.6    | 39                    | 213501                   | 14958                     |
| run 2    | 26.1    | 6                     | 153179                   | 9058                      |
| run 3    | 30.5    | 7                     | 224178                   | 14145                     |

- **The desktop was not stalled.** The login sessions (i3 and everything it
  started) stalled 6-39 ms per run, under the 1 s limit the bench now
  enforces. Global PSI full rose during the runs (avg10 6.4-11.7 after
  them), but global `full` counts the moments every busy task on the host is
  stalled, which the bench scope causes by itself. It is not a desktop
  measure, so the bench no longer prints it.
- **Other processes do swap during a zram run.** They swapped out
  153k-224k pages per run against 111k over the idle interval, so the run
  adds roughly 40k-110k pages (0.2-0.4 GB). zram's pool is not charged to the
  bench scope: zram grows in global RAM, and global reclaim then takes pages
  from other processes too. zswap's pool is charged to the scope, so a zswap
  run does not do this; the host A/B numbers favour zram for the same reason
  as the known bias above. The VM result, pressed system-wide, still picks
  zram.
- **`disk_wb_pages` on a zram host run is background.** The idle interval
  had 20k pages of `pswpout` that zram did not take, the same range as the
  runs (9k-15k), so it is not the bench's. The swapfiles' Used did not grow
  in any interval. That fits other processes writing pages back into
  swapfile slots they still hold from the zswap test (about 17 GB of slots,
  see the switch log), but it was not traced per device. The three A/B zram
  rows were taken before the zswap test, and read 0.

### Raw rows

```tsv
date	env	setup	seed	size_mib	pages	fill_crc	touch_crc	seconds	ratio	psi_some_ms	psi_full_ms	majflt	disk_wb_pages	zswpwb	global_full_avg10	desktop_full_ms	outside_pswpout
2026-11-27T10:59:54Z	vm	zram	20261127	4608	1179648	531769134	2573270970	18.928	3.21	5996	5996	127223	0	0	34.56	na	na
2026-11-27T11:00:14Z	vm	zram	20261127	4608	1179648	531769134	2573270970	13.248	3.21	5782	5782	124816	0	0	39.31	na	na
2026-11-27T11:00:35Z	vm	zram	20261127	4608	1179648	531769134	2573270970	13.393	3.21	6118	6118	124559	0	0	43.00	na	na
2026-11-27T11:02:00Z	vm	zswap	20261127	4608	1179648	531769134	2573270970	28.698	3.15	10366	10360	147757	92	92	38.06	na	na
2026-11-27T11:02:29Z	vm	zswap	20261127	4608	1179648	531769134	2573270970	20.711	3.16	8833	8832	210005	128	128	40.12	na	na
2026-11-27T11:03:04Z	vm	zswap	20261127	4608	1179648	531769134	2573270970	27.756	3.18	12828	12826	127486	0	0	52.34	na	na
2026-11-27T11:16:58Z	host	zram	20261127	6144	1572864	2708526455	3876889511	24.548	2.83	5546	5546	177006	0	0	4.65	14	na
2026-11-27T11:17:33Z	host	zram	20261127	6144	1572864	2708526455	3876889511	30.586	2.82	8223	8223	168862	0	0	4.21	1	na
2026-11-27T11:18:05Z	host	zram	20261127	6144	1572864	2708526455	3876889511	29.029	3.18	7427	7427	172634	0	0	4.97	0	na
2026-11-27T11:20:54Z	host	zswap	20261127	6144	1572864	2708526455	3876889511	49.381	3.21	11684	11684	218408	617001	586700	3.06	6	na
2026-11-27T11:21:45Z	host	zswap	20261127	6144	1572864	2708526455	3876889511	45.383	3.21	8973	8973	208093	584944	453067	9.56	29	na
2026-11-27T11:22:25Z	host	zswap	20261127	6144	1572864	2708526455	3876889511	35.541	3.21	5490	5490	223518	835213	331649	7.50	13	na
```

## Host switch log

- zram → zswap, live: `setup_zswap.sh` ran as a system unit. zram0 held
  9.9 GB (3.6 GB compressed), MemAvailable was 10.4 GB, and the swapoff
  finished in under 35 s. About 3 GB spilled to the swapfiles while it
  drained. After that MemAvailable was 4.3 GB, too little for a host run.
  `echo 4G > /sys/fs/cgroup/user.slice/memory.reclaim` pushed the cold
  pages into the zswap pool (10.9 GB stored in 3.4 GB), which is where zram
  had held them.
- zswap → zram, live: `setup_zram.sh` (one command). All three loader
  entries are byte-identical to their originals in `/var/lib/swap-switch/`,
  and `/proc/cmdline` already said `zswap.enabled=0`, so no reboot was
  needed. Pages still in the zswap pool and on the swapfiles (about 17 GB of
  slots) come back as they fault in; zram takes all new swap-outs again.

## vmbox checks

`lib/tests/vmbox_swap.sh` (phases, run inside a BIOS/GRUB guest):

- **Live switch zram → zswap:** no zram0; zswap reads `Y`, `zstd`, `35`
  and `Y`. After a reboot `/proc/cmdline` carries all four tokens.
- **Revert zswap → zram:** zram0 is back at prio 100 with zstd, zswap reads
  `N`, and after a reboot `/proc/cmdline` has `zswap.enabled=0`.
- **Rerun on the same state:** the GRUB files hash the same, the swap list
  is unchanged and nothing is reported as changed.
- **Exit 3:** zram held 1.7 GB of a 5 GB tmpfs file and MemAvailable was
  50 MB. `setup_zswap.sh` exited 3 with "reboot to apply", leaving zram0
  active and zswap off. The next boot came up on zswap.
- **Hibernate with zswap on:** a fresh guest booted with the zswap cmdline,
  and a 3 GB tmpfs file went into the pool during hibernation (3.0 GB
  stored in 73 MB after resume). `vm wake … systemctl hibernate` gave the `hibernate` verdict, the
  guest resumed with the same boot_id, and zswap still read `Y` and `35`.
- **Not explained:** the guest that ran the benchmarks cold-booted on
  every hibernate (`PM: Image not found`). This happened under zram as well
  as zswap, so the swap setup is not the cause. A fresh guest resumed
  under both its default zswap and `setup_zswap.sh`.
