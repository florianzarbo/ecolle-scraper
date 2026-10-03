# ntfy Notifications from Ecolle

This project sends __[ntfy](https://ntfy.sh)__ notifications with your next "colles", read from a CSV export of your ecolle agenda.

## Expected CSV

Export your colle schedule from ecolle as a CSV file. It must have a header row and at least these columns:

```csv
Date,Matière,Colleur,Jour,Salle,Début,Fin
2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00
2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00
```

- `Date` is read as `YYYY-MM-DD` (the day of the week is not used to compute the date)
- `Début` is the start time, `Fin` the end time
- `Jour` and `Fin` are optional, the other columns are required
- Accents, capitalisation and extra columns are tolerated, so `Matiere` or an extra `Note` column are fine
- An `input/colles.example.csv` sample is included in the repository

Put the file at `input/colles.csv` (or anywhere else, see [`COLLES_CSV_PATH`](configuration.md#colles_csv_path)).

## Getting started

### Docker compose (recommended)

1. Install __[docker](https://docs.docker.com/get-started/get-docker/)__
2. Copy `docker-compose.yml` and `.env.example` to `.env`
3. Put your CSV export at `./input/colles.csv`
4. Edit the required variables in `.env`, see [configuration](configuration.md)
5. Run it once with `docker compose run --rm app`

The container performs a single run and exits. To send the notification every morning, schedule it, for instance with cron:

```
0 7 * * * cd /path/to/ecolle && docker compose run --rm app
```

To use the prebuilt image instead of building locally, replace `build: .` with your image in `docker-compose.yml`:

```yaml
services:
  app:
    image: ghcr.io/florianzarbo/ecolle-scraper:latest
```

### Native

1. Install __[uv](https://docs.astral.sh/uv/getting-started/installation/)__
2. `git clone https://github.com/florianzarbo/ecolle-scraper.git`
3. Put your CSV export at `input/colles.csv`
4. `cp .env.example .env` and edit it, see [configuration](configuration.md)
5. `uv run main.py`

### Tests

The CSV pipeline has a small standard-library test suite:

```
uv run python -m unittest discover -s tests
```

