# .env configuration

This project is configured via environment variables (typically stored in a `.env` file).

Only the variables that are **not commented out** in `.env.example` are required; commented ones are optional.

Since version 2.0.0 the schedule is read from a CSV file, see [CSV format](csv.md) for the expected content.

## Setup

### With docker compose (recommended)

#### docker-compose.yml

```yaml
services:
  app:
    build: .
    # or use the prebuilt image:
    # image: ghcr.io/florianzarbo/ecolle-scraper:latest
    env_file:
      - .env
    volumes:
      # Upload your CSV export here
      - ./input:/app/input:ro
      # Keeps the normalised agenda between runs
      - ./output:/app/output
```

Then, with your CSV at `./input/colles.csv`:

```
docker compose run --rm app
```

The container performs a single run and exits, so it can be scheduled (e.g. with cron).

### .env file

1. Copy the template:

        cp .env.example .env


2. Edit `.env` and set the required values.
3. Do **not** commit `.env` (it contains secrets).

## Required variables

### `NTFY_TOPIC`

The ntfy topic to publish notifications to.

- Example:

        NTFY_TOPIC=YourTopicName


- Tip: If using a public ntfy server, use a random topic name to reduce the risk of others guessing it.

***

### `NTFY_TITLE`

The title used for notifications.

- Example:

        NTFY_TITLE=Today's colles


- Tip: Keep quotes if there are spaces.

***

### `NUMBER_OF_COLLES_TO_SHOW`

How many upcoming colles to send, starting from the soonest one.

- Example:

        NUMBER_OF_COLLES_TO_SHOW=1


- Type: integer (`1`, `2`, `3`, …)
- Default: `1`

***

### `COLLES_CSV_PATH`

Path of the CSV export to read, **inside the container**.

- Default: `input/colles.csv`
- Examples:

        COLLES_CSV_PATH=input/colles.csv
        COLLES_CSV_PATH=/app/input/colles.csv


- Notes:
    - This is a container path, not a path on your machine. With the provided `docker-compose.yml`, the `input/` folder of the host is mounted read-only at `/app/input`, so `./input/colles.csv` on your machine is `input/colles.csv` (or `/app/input/colles.csv`) here.
    - The script runs with `/app` as its working directory, so relative paths resolve against `/app`.
    - The file must be world-readable (`chmod a+r`): if it is only readable by its owner, the container may not be able to read it.
    - If the file is not found, the message lists the CSV files that *are* present at that location.

***

### `DISABLE_ECOLLE_FETCH`

Set to `true` to never contact the ecolle website.

- Default: `false`
- Example:

        DISABLE_ECOLLE_FETCH=true


- Notes:
    - With this on, the CSV file is the only source: if it is missing, the run fails with an explanatory message instead of trying to log in to ecolle.
    - Without it, a missing CSV file makes the script fall back to scraping ecolle (only possible if `BASE_URL`, `COLLES_USERNAME` and `COLLES_PASSWORD` are set).
    - `DISABLE_SCRAPER_FALLBACK` and `NO_SCRAPE` are accepted as alternative names.
    - `DISABLE_ECALLE_FETCH` (misspelled) is still accepted, it was shipped that way in v2.1.0 and is deprecated.

***

## Optional variables

### `NTFY_FORMAT`

You can change the format of your notification with a format string.

- Variables need to be inside `{}`, and you can put any text between them.
- Available variables:

    1. `matiere`
    2. `date`
    3. `heure`
    4. `fin`
    5. `salle`
    6. `colleur`
    7. `jour`
    8. `date_time` (date and start time together, e.g. `2026-09-24 17:00`)

- Default : `{matiere} {date} {heure} {salle} {colleur}`

- Example:

        NTFY_FORMAT={matiere} le {date} à {heure}, salle {salle} avec {colleur}


- Notes: an unknown field name stops the run with a message listing the available fields.

---

### `AGENDA_CSV_PATH`

Where the normalised agenda is cached between runs. It is used to keep sending notifications when the CSV export cannot be read.

- Default: `output/agenda.csv`
- Example:

        AGENDA_CSV_PATH=output/agenda.csv


- Notes: Mount this path as a volume if you want the cache to survive the container, as done in the provided `docker-compose.yml`.

---

### `NTFY_SERVER`

URL of your ntfy instance.

- Default: `https://ntfy.sh`
- Set this only if you use a custom/self-hosted ntfy server.
- Example:

        NTFY_SERVER=https://ntfy.example.org

***

### `SELF_SIGNED_CERTIFICATE`

Enable only if your server uses a self-signed TLS certificate.

- Default: `False`
- Example:

        SELF_SIGNED_CERTIFICATE=true

***

### `ROOT_CA_PATH`

Path to the Root CA file (PEM) that signed your TLS certificate.

- Example:

        ROOT_CA_PATH=/path/to/rootCA.pem

***

## Scraper fallback (optional)

When no CSV file is found at `COLLES_CSV_PATH`, the script falls back to the pre-2.0.0 behaviour and scrapes your ecolle instance. Those variables are only needed in that case, and the whole fallback can be turned off with [`DISABLE_ECOLLE_FETCH`](#disable_ecolle_fetch).

### `BASE_URL`

Base URL of your institution's e-colle website.

- Example:

        BASE_URL=https://ecolle.example.com

- Notes: Include `https://` and use the site's base URL (no extra path unless required by your institution).

***

### `COLLES_USERNAME`

Your e-colle username (used to authenticate and fetch your colle agenda).

- Example:

        COLLES_USERNAME=YourUsername

***

### `COLLES_PASSWORD`

Your e-colle password (used to authenticate).

- Example:

        COLLES_PASSWORD=YourPassword

- Security: Treat as a secret; prefer secret storage (CI secrets, systemd credentials, etc.) when possible.

***

## Example `.env`

```env
COLLES_CSV_PATH=input/colles.csv
DISABLE_ECOLLE_FETCH=true
NUMBER_OF_COLLES_TO_SHOW=2

NTFY_TOPIC=mp2i-9f3a2c1d
NTFY_TITLE=Today's colles

# Optional:
# NTFY_SERVER=https://ntfy.example.org
# NTFY_FORMAT={matiere} {date} {heure} {salle} {colleur}
# AGENDA_CSV_PATH=output/agenda.csv
```

## Troubleshooting

- **`CSV file not found`**: the message lists the CSV files present at that location and reminds you that `COLLES_CSV_PATH` is a *container* path. With the provided compose file, `./input/colles.csv` on your machine is `input/colles.csv` inside the container.
- **The container ignores the CSV and tries to log in to ecolle**: you are running the pre-2.0.0 image. `docker compose pull` (or `docker compose build --pull`) and check `docker run --rm <image> --help`-free output starts with `[*] Reading CSV:`.
- **`exists but cannot be read`**: the file is not world-readable, run `chmod a+r input/colles.csv`.
- No notifications: Verify `NTFY_TOPIC` (and `NTFY_SERVER` if you set it).
- `missing column(s) …`: the CSV is not the expected one, check [CSV format](csv.md). Note that a semicolon-separated export is not accepted.
- `no usable row found`: check that the dates look like `2026-09-24` and the times like `17:00`.
- The run stops with a message but you still get notifications: the CSV could not be read and the agenda cached in `AGENDA_CSV_PATH` was used instead.
- Nothing is sent although the CSV contains colles: only colles that are still in the future are sent, and `NUMBER_OF_COLLES_TO_SHOW` limits how many.
- TLS issues with self-hosted ntfy: Set `SELF_SIGNED_CERTIFICATE=true` and provide a valid `ROOT_CA_PATH`.
- TLS issues with the scraper fallback: same, `SELF_SIGNED_CERTIFICATE` and `ROOT_CA_PATH` are used for the ecolle connection too.
