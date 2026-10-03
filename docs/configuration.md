# Configuration

This project is configured through environment variables, usually provided by a
`.env` file next to `docker-compose.yml`.

## At a glance

| Variable | Default | Required | Purpose |
| -------- | ------- | -------- | ------- |
| `NTFY_TOPIC` | *(empty)* | **yes** | where notifications are published |
| `COLLES_CSV_PATH` | `input/colles.csv` | no | path of your export, **inside the container** |
| `DISABLE_ECOLLE_FETCH` | `false` | no | never contact ecolle; the CSV is the only source |
| `NUMBER_OF_COLLES_TO_SHOW` | `1` | no | how many upcoming colles to send |
| `NTFY_TITLE` | *(empty)* | no | notification title |
| `NTFY_FORMAT` | see below | no | wording of the notification |
| `NTFY_SERVER` | `https://ntfy.sh` | no | your own ntfy instance |
| `AGENDA_CSV_PATH` | `output/agenda.csv` | no | cache of the last run |
| `SELF_SIGNED_CERTIFICATE` | `false` | no | accept a self-signed TLS certificate |
| `ROOT_CA_PATH` | *(empty)* | no | CA that signed that certificate |
| `BASE_URL`, `COLLES_USERNAME`, `COLLES_PASSWORD` | *(empty)* | no | only for the scraper fallback |

`.env.example` is the template: copy it and change `NTFY_TOPIC`.

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
      # Your CSV export goes here
      - ./input:/app/input:ro
      # Keeps the normalised agenda between runs
      - ./output:/app/output
```

Then, with your CSV at `./input/colles.csv`:

```
docker compose run --rm app
```

The container performs a single run and exits, so it can be scheduled, see
[Getting started](getting-started.md#6-schedule-it).

### .env file

1. Copy the template:

        cp .env.example .env


2. Edit `.env`, see the variables below.
3. Do **not** commit `.env` (it may contain secrets).

## Required variables

### `NTFY_TOPIC`

The ntfy topic to publish notifications to.

- Example:

        NTFY_TOPIC=YourTopicName


- Tip: If using a public ntfy server, use a random topic name to reduce the risk of others guessing it.

- Notes: without it the run stops with `NTFY_TOPIC is not set, there is nowhere to send the notification` and exit code `1`.

***

## Optional variables

### `COLLES_CSV_PATH`

Path of the CSV export to read, **inside the container**.

- Default: `input/colles.csv`
- Examples:

        COLLES_CSV_PATH=input/colles.csv
        COLLES_CSV_PATH=/app/input/colles.csv
        COLLES_CSV_PATH=./input/colles.csv


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
    - `DISABLE_ECALLE_FETCH`, the misspelt name shipped in 2.1.0, still works but is deprecated.

***

### `NUMBER_OF_COLLES_TO_SHOW`

How many upcoming colles to send, starting from the soonest one.

- Default: `1`
- Example:

        NUMBER_OF_COLLES_TO_SHOW=2


- Notes: must be a whole number of 1 or more. Anything else stops the run with
  an explicit message rather than sending nothing silently. Only colles that
  have not started yet are counted, see
  [Troubleshooting](troubleshooting.md#the-run-sends-nothing).

***

### `NTFY_TITLE`

The title used for notifications. Optional, empty by default.

- Example:

        NTFY_TITLE=Today's colles


- Tip: Keep quotes if there are spaces.

***
    - `DISABLE_ECALLE_FETCH` (misspelled) is still accepted, it was shipped that way in v2.1.0 and is deprecated.

***


### `NTFY_FORMAT`

You can change the format of your notification with a format string.

Fields need to be inside `{}`, and you can put any text between them. Dates are written in French (`16 janvier`) and times the French way (`15h00`), no matter the locale of the machine running the container.

#### Fields from the CSV

| Field       | Example              | Notes                                    |
| ----------- | -------------------- | ---------------------------------------- |
| `matiere`   | `Mathématiques`      | Subject                                  |
| `colleur`   | `M Jouve`            | Who examines you                         |
| `salle`     | `P103`               | Room                                     |
| `fin`       | `16:00`              | End time, may be empty                   |
| `date`      | `2027-01-16`         | Raw ISO date, for technical use          |
| `heure`     | `15:00`              | Raw start time                           |
| `date_time` | `2027-01-16 15:00`   | Raw date and start time                  |

#### Derived fields

| Field         | Example                | Notes                                          |
| ------------- | ---------------------- | ---------------------------------------------- |
| `jour`        | `samedi`               | Computed from the date, never from the export  |
| `date_courte` | `16 janvier`           | Day and month                                  |
| `date_longue` | `samedi 16 janvier`    | Day name, day and month                        |
| `date_annee`  | `16 janvier 2027`      | Day, month and year                            |
| `heure_debut` | `15h00`                | Start time                                     |
| `heure_fin`   | `15h00 - 16h00`        | Start and end time, or just `15h00`            |
| `date_heure`  | `16 janvier 15h00`     | Day, month and start time                      |

Because `jour` is derived from the date, a wrong or missing `Jour` column in the CSV cannot make the notification lie about the day.

- Default : `{jour} {date_courte} {heure_debut} {salle} - {matiere} ({colleur})`, which renders as:

        samedi 16 janvier 15h00 P103 - Mathématiques (M Jouve)

- Examples:

        NTFY_FORMAT={matiere} {jour} {date_courte} {heure_debut} {salle}
        NTFY_FORMAT={date_longue} {heure_fin} - {matiere} en {salle} ({colleur})
        NTFY_FORMAT={matiere} le {date_courte} à {heure_debut}, salle {salle}

- Fallback syntax: `{field|text}` renders `text` when `field` is empty, which is
  useful for the optional `Fin` column:

        NTFY_FORMAT={matiere} {fin|fin inconnue} ({jour|jour inconnu})

  which renders as `Mathématiques fin inconnue (samedi)` when the export has no
  end time.


- Notes: an unknown field name stops the run with a message listing the available fields. Extra spaces and punctuation left behind by empty fields are cleaned up. If a row has no readable date at all, the date fields render empty instead of stopping the run.

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
# NTFY_FORMAT={jour} {date_courte} {heure_debut} {salle} - {matiere} ({colleur})
# AGENDA_CSV_PATH=output/agenda.csv
```

## Troubleshooting

Every error message, the exit codes and the "nothing was sent" checklist have
their own page: [Troubleshooting](troubleshooting.md).

The two mistakes that account for most problems:

- `COLLES_CSV_PATH` is a path **inside the container**, not on your machine.
- only colles that have **not started yet** are sent, so a file of past dates
  sends nothing and still exits `0`.
