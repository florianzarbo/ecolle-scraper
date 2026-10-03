# Ecolle notifications

Sends __[ntfy](https://ntfy.sh)__ notifications with your next "colles", read from a CSV export of your ecolle agenda.

```csv
Date,Matière,Colleur,Jour,Salle,Début,Fin
2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00
```

becomes

```
mardi 6 octobre 16h00 L005 - Mathématiques (M Jouve)
```

## How it works

```
your export ──▶ reads the CSV ──▶ keeps the colles still to come ──▶ sends them to ntfy
```

One run sends the next colles and exits, so it is meant to be scheduled. There is no server and no state besides a small cache of the last run.

Only colles that have **not started yet** are sent. A file containing only past dates legitimately sends nothing and exits `0`.

## Where to go next

- [Getting started](getting-started.md) — export the CSV, run the container, verify it worked, schedule it
- [CSV format](csv.md) — the file the tool expects, and what it tolerates
- [Configuration](configuration.md) — every setting, and the message format
- [Troubleshooting](troubleshooting.md) — when nothing is sent, and what the exit codes mean
- [Upgrading](upgrading.md) — coming from version 1.x
- [Development](development.md) — the test suite, the module layout, building the image
