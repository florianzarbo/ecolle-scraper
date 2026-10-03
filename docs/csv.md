# CSV format

Starting with version 2.0.0, the schedule is read from a CSV file rather than fetched from an ecolle instance. This page describes the expected file.

## Where to put the file

By default the script reads:

```
input/colles.csv
```

relative to the working directory. Inside the container that is `/app/input/colles.csv`, so with the provided `docker-compose.yml` you only have to drop your file in the `input/` folder next to `docker-compose.yml`.

To use another location, set [`COLLES_CSV_PATH`](configuration.md#colles_csv_path):

```
COLLES_CSV_PATH=/app/data/my-colles.csv
```

## Expected content

The file must be comma separated and start with a header row:

```csv
Date,Matière,Colleur,Jour,Salle,Début,Fin
2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00
2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00
2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00
```

## Columns

| Column    | Required | Meaning                                             |
| --------- | -------- | --------------------------------------------------- |
| `Date`    | yes      | Date of the colle, `YYYY-MM-DD`                     |
| `Matière` | yes      | Subject, e.g. `Mathématiques`                       |
| `Colleur` | yes      | Who examines you                                    |
| `Salle`   | yes      | Room                                                |
| `Début`   | yes      | Start time, `HH:MM`                                 |
| `Jour`    | no       | Day name, used by the `{jour}` notification field   |
| `Fin`     | no       | End time, used by the `{fin}` notification field    |

### Date and time

`Date` is parsed on its own: the `Jour` column is never used to work out the date, so an inconsistent day name cannot shift your schedule. Accepted layouts are `YYYY-MM-DD` (recommended), `DD/MM/YYYY`, `DD-MM-YYYY` and `DD.MM.YYYY`.

`Début` accepts `HH:MM`, `HH:MM:SS`, `HHhMM` and `HHh`.

### Tolerated variations

The reader is deliberately forgiving:

- accents are optional: `Matiere` works as well as `Matière`
- capitalisation, surrounding spaces, `_` and `-` in headers are ignored
- a UTF-8 BOM (as produced by Excel) is stripped
- extra columns are ignored
- blank lines are skipped
- unsupported header spellings are reported in the error message

Rows with an unreadable date or time are skipped with a warning, and the rest of the file is still used. A row of data may not span several lines.

## What happens on an error

If the CSV file is missing, or cannot be used (wrong separator, missing required column, no usable row), the run stops with a clear message. When a previously normalised agenda is still present in `/app/output`, it is used instead so you keep receiving notifications; the exit code stays `0` only if a CSV or that cached agenda was usable.

## Sample file

An `input/colles.example.csv` sample is included in the repository. Copy it and replace the rows with your own:

```
cp input/colles.example.csv input/colles.csv
```
