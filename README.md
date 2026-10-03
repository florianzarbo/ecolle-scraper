
# ntfy Notifications from Ecolle

This project sends __[ntfy](https://ntfy.sh)__ notifications with your next "colles", read from a CSV export of your ecolle agenda.

Since version 2.0.0 the colles come from a CSV file, so there is no need to log in to an ecolle instance any more. Upload your CSV, run the container, get the notification.

## Quick start (docker compose)

1. Install __[docker](https://docs.docker.com/get-started/get-docker/)__
2. Copy `docker-compose.yml`, then `cp .env.example .env`
3. Put your CSV export at `./input/colles.csv`
4. Set at least `NTFY_TOPIC` in `.env`
5. `docker compose run --rm app`

The container does a single run and exits, which makes it easy to schedule, for instance with cron:

```
0 7 * * * cd /path/to/ecolle && docker compose run --rm app
```

Full documentation [here](https://florianzarbo.github.io/ecolle-scraper/)
