# sql_drills

MySQL 8 practice drills graded like an online judge: the query's output must
match the expected text exactly. Engine: Docker image `mysql:8.0.33`
(pinned on purpose; do not bump). Needs Docker and your user in the `docker`
group.

```bash
python3 -m python_pkg.sql_drills start               # container + wait (<60 s)
python3 -m python_pkg.sql_drills list                # ids and titles
python3 -m python_pkg.sql_drills show 01             # task, schema, output sample
python3 -m python_pkg.sql_drills check 01 my.sql     # grade my.sql (exit 0 = pass)
python3 -m python_pkg.sql_drills stop                # remove the container
```

Drills are addressed by full id (`01_pivot_sum`) or leading number (`01`).

## Grading rules

Output is `mysql -B -N` style: no header, tab separators become single
spaces, `NULL` prints as `NULL`, trailing whitespace is stripped per line.
Nothing else is normalised: case, decimal places and row order are strict, so
add the `ORDER BY` the task asks for. On mismatch you get an expected vs
actual diff per line. A fresh database is built for every check.

## Layout

- `fixtures/<id>/` holds `DOCS-task.md`, `schema.sql`, `expected.txt`.
- Reference solutions live only in `tests/solutions/`; `show` and `check`
  never print them.
- `tests/test_live.py` runs every reference against the container (marker
  `docker`, skipped when the container is down).
