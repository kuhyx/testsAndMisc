# sql_drills

CLI over the shared `sql_drills` package (kuhyx/utils, tag `sql-drills-v0.1.0`):
drills, fixtures, reference solutions and grading rules live there.

```bash
python3 -m python_pkg.sql_drills start               # container + wait (<60 s)
python3 -m python_pkg.sql_drills list                # ids and titles
python3 -m python_pkg.sql_drills show 01             # task, schema, output sample
python3 -m python_pkg.sql_drills check 01 my.sql     # grade my.sql (exit 0 = pass)
python3 -m python_pkg.sql_drills stop                # remove the container
```
