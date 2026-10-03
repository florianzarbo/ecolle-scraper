
# ntfy Notifications from Ecolle

This project sends __[ntfy](https://ntfy.sh)__ notifications with your next "colles", read from a CSV export of your ecolle agenda.

Since version 2.0.0 the colles come from a CSV file, so there is no need to log in to an ecolle instance any more. Upload your CSV, run the container, get the notification.

## Quick start (docker compose)

1. Install __[docker](https://docs.docker.com/get-started/get-docker/)__
2. Copy `docker-compose.yml`, then `cp .env.example .env`
3. Put your CSV export at `./input/colles.csv`
4. Set at least `NTFY_TOPIC` in `.env`
5. `docker compose run --rm app`

`COLLES_CSV_PATH` is a path *inside* the container: the compose file mounts `./input` on `/app/input`, so `./input/colles.csv` beside `docker-compose.yml` becomes `input/colles.csv` in the container. Set `DISABLE_ECALLE_FETCH=true` to make the CSV the only source, so a missing file fails loudly instead of falling back to scraping ecolle.

The container does a single run and exits, which makes it easy to schedule, for instance with cron:

```
0 7 * * * cd /path/to/ecolle && docker compose run --rm app
```

Full documentation [here](https://florianzarbo.github.io/ecolle-scraper/)
