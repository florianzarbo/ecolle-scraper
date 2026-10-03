
# ntfy Notifications from Ecolle

This project sends __[ntfy](https://ntfy.sh)__ notifications with your next "colles", read from a CSV export of your ecolle agenda.

Since version 2.0.0 the colles come from a CSV file, so there is no need to log in to an ecolle instance any more. Upload your CSV, run the container, get the notification.

Notifications look like this:

```
jeudi 15 octobre 17h00 P101 - Mathématiques (M Bouzouina)
mardi 13 octobre 15h00 L216F - Physique (M Combette)
```

Dates are written in French (`15 octobre`) and times the French way (`17h00`), regardless of the machine's locale. The day name is computed from the date, so a wrong `Jour` column cannot mislead you. See [NTFY_FORMAT](https://florianzarbo.github.io/ecolle-scraper/configuration/#ntfy_format) to change the wording.

## Quick start (docker compose)

1. Install __[docker](https://docs.docker.com/get-started/get-docker/)__
2. Copy `docker-compose.yml`, then `cp .env.example .env`
3. Put your CSV export at `./input/colles.csv`
4. Set at least `NTFY_TOPIC` in `.env`
5. `docker compose run --rm app`

`COLLES_CSV_PATH` is a path *inside* the container: the compose file mounts `./input` on `/app/input`, so `./input/colles.csv` beside `docker-compose.yml` becomes `input/colles.csv` in the container. Set `DISABLE_ECOLLE_FETCH=true` to make the CSV the only source, so a missing file fails loudly instead of falling back to scraping ecolle.

The container does a single run and exits, which makes it easy to schedule, for instance with cron:

```
0 7 * * * cd /path/to/ecolle && docker compose run --rm app
```

Full documentation [here](https://florianzarbo.github.io/ecolle-scraper/)
