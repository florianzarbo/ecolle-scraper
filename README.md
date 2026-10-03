# ntfy Notifications from Ecolle

Sends __[ntfy](https://ntfy.sh)__ notifications with your next "colles", read from a CSV export of your ecolle agenda.

```
mardi 6 octobre 16h00 L005 - Mathématiques (M Jouve)
jeudi 8 octobre 18h00 P103 - Anglais (M Taghouan)
```

Dates are written in French (`6 octobre`) and times the French way (`16h00`), whatever the machine's locale. The day name is computed from the date, so a wrong `Jour` column in the export cannot mislead you.

## How it works

```
your export ──▶ reads the CSV ──▶ keeps the colles still to come ──▶ sends them to ntfy
```

One run sends the next colles and exits, so it is meant to be scheduled. No server, no database: just a container, a CSV file and a notification topic.

> **Only colles that have not started yet are sent.** A file containing only past dates legitimately sends nothing and exits `0`. This is the most common cause of "it does nothing" — see [Troubleshooting](https://ecolle-scraper.zarbo.dev/troubleshooting/).

## Quick start

1. **Export your colles from ecolle** as a comma-separated UTF-8 CSV file.
2. Put it in an `input` folder next to `docker-compose.yml`:

   ```
   my-ecolle/
   ├── docker-compose.yml
   ├── .env
   └── input/
       └── colles.csv
   ```

3. `cp .env.example .env`, then set `NTFY_TOPIC` to a topic name of your choice (a random string, if you use the public ntfy server).
4. Run it once:

   ```
   docker compose run --rm app
   ```

5. Subscribe to the same topic in the ntfy app. You should receive one notification per colle.

The expected CSV looks like this; the full description is in the [CSV format](https://ecolle-scraper.zarbo.dev/csv/) page.

```csv
Date,Matière,Colleur,Jour,Salle,Début,Fin
2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00
2026-10-08,Anglais,M Taghouan,jeudi,P103,18:00,19:00
```

### Without cloning anything

```
docker run --rm \
  -e NTFY_TOPIC=your-topic \
  -e DISABLE_ECOLLE_FETCH=true \
  -v "$PWD/input:/app/input:ro" \
  -v "$PWD/output:/app/output" \
  ghcr.io/florianzarbo/ecolle-scraper:latest
```

### Schedule it

```
0 7 * * * cd /path/to/my-ecolle && docker compose run --rm app >> run.log 2>&1
```

Redirect the output: a scheduled run that fails is otherwise completely silent. See [Getting started](https://ecolle-scraper.zarbo.dev/getting-started/#6-schedule-it) for a systemd timer.

## Configuration

Everything is optional except `NTFY_TOPIC`. `COLLES_CSV_PATH` is a path **inside** the container: the compose file mounts `./input` on `/app/input`, so `./input/colles.csv` beside `docker-compose.yml` becomes `input/colles.csv` in the container.

`DISABLE_ECOLLE_FETCH=true` makes the CSV the only source, so a mistake in the path is reported instead of turning into an attempt to scrape ecolle.

The full list, the message format and its fields are in [Configuration](https://ecolle-scraper.zarbo.dev/configuration/).

## Documentation

- [Getting started](https://ecolle-scraper.zarbo.dev/getting-started/) — export, run, verify, schedule
- [CSV format](https://ecolle-scraper.zarbo.dev/csv/) — the file the tool expects
- [Configuration](https://ecolle-scraper.zarbo.dev/configuration/) — every setting and message field
- [Troubleshooting](https://ecolle-scraper.zarbo.dev/troubleshooting/) — when nothing is sent
- [Upgrading](https://ecolle-scraper.zarbo.dev/upgrading/) — coming from version 1.x
- [Development](https://ecolle-scraper.zarbo.dev/development/) — tests and building the image

## Tests

```
uv run python -m unittest discover -s tests
```

Around 130 standard-library tests, no extra dependencies.

## License

See [LICENSE](LICENSE).
