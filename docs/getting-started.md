# Getting started

## What it does

Every time it runs, the tool:

1. reads your colles from a CSV file you exported from ecolle;
2. keeps the ones that have not started yet;
3. sends the closest ones as __[ntfy](https://ntfy.sh)__ notifications.

It is meant to be scheduled, so the container performs a single run and exits.
There is no server and no state besides a small cache file.

## 1. Export your colles

The tool reads a CSV export of your agenda; it has no way of downloading it for
you any more.

On your ecolle instance, open your agenda/colloscope page and use the export
button (or the print/export menu of your browser) to save it as a CSV file.
Make sure the export is **comma separated** and **UTF-8**, not the "CSV UTF-16"
or "ANSI" that spreadsheet programs sometimes default to.

The file must contain a header row with at least `Date`, `Matière`, `Colleur`,
`Salle` and `Début`, like this:

```csv
Date,Matière,Colleur,Jour,Salle,Début,Fin
2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00
2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00
```

The full description is in [CSV format](csv.md). If your export has different
column names, it can usually still be used as long as the required ones are
recognisable.

## 2. Put the file next to the compose file

```
my-ecolle/
├── docker-compose.yml
├── .env
└── input/
    └── colles.csv      <- your export
```

The `input` folder is mounted read-only into the container at `/app/input`, and
`COLLES_CSV_PATH` defaults to `input/colles.csv`, which is that file. A sample
is provided: `cp input/colles.example.csv input/colles.csv` gives you a file to
try the tool with. Make sure it is readable: `chmod a+r input/colles.csv`.

## 3. Configure

Copy `.env.example` to `.env`. Only `NTFY_TOPIC` really has to change:

```env
COLLES_CSV_PATH=input/colles.csv
DISABLE_ECOLLE_FETCH=true
NUMBER_OF_COLLES_TO_SHOW=1

NTFY_TOPIC=your-random-topic-name
NTFY_TITLE=Today's colles
```

All the variables are described in [Configuration](configuration.md).

## 4. Run it

### With docker compose (recommended)

```
docker compose run --rm app
```

Use `run`, not `up`: the container is meant to do one run and exit. The output
looks like this:

```
[*] Reading CSV: input/colles.csv
[+] Parsed 37 colles from CSV
[+] Saved 37 rows to output/agenda.csv
[*] next colle: 2026-10-06 16:00
```

`docker compose up -d` also works, but it leaves a stopped container behind
each time.

### Without the repository

If you would rather not clone anything, mount the two folders directly:

```
docker run --rm \
  -e NTFY_TOPIC=your-random-topic-name \
  -e DISABLE_ECOLLE_FETCH=true \
  -v "$PWD/input:/app/input:ro" \
  -v "$PWD/output:/app/output" \
  ghcr.io/florianzarbo/ecolle-scraper:latest
```

Pin the version (`:2.4`) instead of `latest` if you prefer predictable
upgrades.

### Natively, without Docker

```
git clone https://github.com/florianzarbo/ecolle-scraper.git
cd ecolle-scraper
cp .env.example .env      # then edit it
cp input/colles.example.csv input/colles.csv   # then replace with your export
uv run main.py
```

`uv` is only used to manage the environment; the tool itself needs nothing but
the standard library plus `requests` and `python-dotenv` installed from
`pyproject.toml`.

## 5. Check that it worked

1. Subscribe to your topic in the ntfy app, or open
   `https://ntfy.sh/<your-topic>` in a browser.
2. Run the tool again.
3. You should see one notification per colle, for the
   `NUMBER_OF_COLLES_TO_SHOW` closest ones.

Nothing arrived? Almost always the CSV contains no *future* colle, see
[Troubleshooting](troubleshooting.md#the-run-sends-nothing).

## 6. Schedule it

### cron

```
0 7 * * * cd /path/to/my-ecolle && docker compose run --rm app >> run.log 2>&1
```

Two things to watch:

* **Redirect the output**, otherwise the messages are lost and a failure is
  invisible.
* **cron has a minimal `PATH`.** If `docker` is not found, use its full path
  (`/usr/bin/docker`) or set `PATH` at the top of the crontab.

### systemd timer

`/etc/systemd/system/ecolle.service`:

```ini
[Unit]
Description=Send the colle notifications

[Service]
Type=oneshot
WorkingDirectory=/path/to/my-ecolle
ExecStart=/usr/bin/docker compose run --rm app
```

`/etc/systemd/system/ecolle.timer`:

```ini
[Unit]
Description=Send the colle notifications every morning

[Timer]
OnCalendar=*-*-* 07:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Then:

```
systemctl enable --now ecolle.timer
journalctl -u ecolle.service      # to read the last run
```

`Persistent=true` runs the job after a boot that was missed, which matters if
the machine is not always on.

## Keeping the CSV up to date

The tool never updates the CSV itself: it only reads it. Export a fresh file
whenever your schedule changes, overwrite `input/colles.csv`, and the next run
picks it up. Nothing else has to be restarted.

Keep the previous file if you want to be able to roll back; the tool also keeps
a normalised copy of the last run in `output/agenda.csv`, which is used if the
CSV cannot be read.

## Next

* [CSV format](csv.md) — the exact file the tool expects
* [Configuration](configuration.md) — every setting
* [Troubleshooting](troubleshooting.md) — when nothing is sent
* [Upgrading](upgrading.md) — coming from version 1.x
* [Development](development.md) — running the tests
