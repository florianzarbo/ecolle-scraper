# CSV format

Starting with version 2.0.0, the schedule is read from a CSV file rather than fetched from an ecolle instance. This page describes the expected file.

## Where to put the file

By default the script reads, **inside the container**:

```
input/colles.csv
```

The script runs with `/app` as its working directory, so that is `/app/input/colles.csv`. The provided `docker-compose.yml` mounts the `input/` folder that sits next to it onto `/app/input`:

```yaml
volumes:
  - ./input:/app/input:ro
```

So on your server you only have to create an `input` folder next to `docker-compose.yml` and drop your export in it:

```
my-ecolle/
├── docker-compose.yml
├── .env
└── input/
    └── colles.csv      <- your export
```

`COLLES_CSV_PATH` is a path *inside the container*. These two are equivalent and both work:

```
COLLES_CSV_PATH=input/colles.csv
COLLES_CSV_PATH=/app/input/colles.csv
```

If you want a single file elsewhere, mount it explicitly instead:

```yaml
volumes:
  - /srv/colles/colles.csv:/app/data/colles.csv:ro
```

with `COLLES_CSV_PATH=/app/data/colles.csv`.

The file must be world-readable (`chmod a+r input/colles.csv`): a file that is only readable by its owner is not always readable inside the container.

## Expected content

The file must be comma separated and start with a header row:

```csv
Date,Matière,Colleur,Jour,Salle,Début,Fin
2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00
2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00
2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00
```

## Columns

| Column    | Required | Meaning                                          |
| --------- | -------- | ------------------------------------------------ |
| `Date`    | yes      | Date of the colle, `YYYY-MM-DD`                  |
| `Matière` | yes      | Subject, e.g. `Mathématiques`                    |
| `Colleur` | yes      | Who examines you, shown by the `{colleur}` field |
| `Salle`   | yes      | Room, shown by the `{salle}` field               |
| `Début`   | yes      | Start time, `HH:MM`                              |
| `Fin`     | no       | End time, used by the `{fin}` and `{heure_fin}` fields |
| `Jour`    | no       | Day name. **Stored but never used**: the day is computed from `Date`, so an inconsistent value cannot mislead you |

### Date and time

`Date` is parsed on its own, so a wrong `Jour` cannot shift your schedule. Accepted layouts are `YYYY-MM-DD` (recommended), `DD/MM/YYYY`, `DD-MM-YYYY` and `DD.MM.YYYY`.

`Début` accepts `HH:MM`, `HH:MM:SS`, `HHhMM` and `HHh`.

### Tolerated variations

The reader is deliberately forgiving:

- accents are optional: `Matiere` works as well as `Matière`
- capitalisation, surrounding spaces, `_` and `-` in headers are ignored
- a UTF-8 BOM (as produced by Excel) is stripped
- extra columns are ignored: any header the tool does not recognise is simply skipped
- blank lines are skipped
- a duplicate column is refused, rather than letting the last one silently win

Rows with an unreadable date or time are skipped with a warning, and the rest of the file is still used. A row of data may not span several lines.

### Encodings

The file must be UTF-8. Excel's "CSV UTF-16" and "ANSI" exports are refused with an explicit message; re-export as **CSV UTF-8**. A UTF-16 byte-order mark is recognised and named in the error.

## Fetching from ecolle

By default, when the CSV file is missing the script falls back to logging in to your ecolle instance, as it did before 2.0.0. That fallback needs `BASE_URL`, `COLLES_USERNAME` and `COLLES_PASSWORD`, and fails with an explanatory message when they are not set. Since the instance is usually unreachable, it is better to switch it off:

```
DISABLE_ECOLLE_FETCH=true
```

The CSV file then becomes the only source. If it is missing, the run stops immediately with a message explaining what was looked for, instead of trying to reach ecolle. This is a good way to be sure the container is really using your file.

## What happens on an error

The two situations behave differently, on purpose:

| Situation | What happens |
| --------- | ------------ |
| CSV file **missing** | the scraper fallback is tried; if it is disabled or unavailable, the run stops with an explanation and exit code `1`. The cache is **not** used. |
| CSV file **present but unusable** (wrong separator, missing column, no usable row, bad encoding) | the run continues from the agenda cached by an earlier run, so you keep receiving notifications, and prints why. Exit code `1` only if there is no usable cache either. |

## Sample file

An `input/colles.example.csv` sample is included in the repository. Copy it and replace the rows with your own:

```
cp input/colles.example.csv input/colles.csv
```
