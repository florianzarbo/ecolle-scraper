# Troubleshooting

## The run sends nothing

This is the most common report, and in almost every case the program worked
correctly. The colles are selected like this:

1. the agenda is read and sorted by date;
2. **only colles that have not started yet** are kept;
3. the `NUMBER_OF_COLLES_TO_SHOW` soonest of those are sent.

So a CSV that only contains past dates sends nothing and still exits `0`:

```
[*] No upcoming colle to notify about
```

Check, in this order:

1. **Are the dates in the future?** Compare them with `date` on the machine.
2. **Is the date parsed at all?** A line such as
   `[!] file.csv:4: skipped row (unrecognised date ...)` means the row was
   dropped. Dates must be `YYYY-MM-DD` (or `DD/MM/YYYY`).
3. **Is `NUMBER_OF_COLLES_TO_SHOW` at least 1?**
4. **Is `NTFY_TOPIC` set?** Without it the run stops with
   `NTFY_TOPIC is not set, there is nowhere to send the notification`.
5. **Did the notification reach the server?** A wrong topic name is silent by
   design: ntfy accepts any topic. Subscribe to the same topic in the ntfy app
   or at `https://ntfy.sh/<topic>` and run the tool again.

## Nothing appears in the container logs

`docker compose run --rm app` prints everything on the console. When the run is
started from cron or a systemd timer, add the output redirection shown in
[Getting started](getting-started.md#6-schedule-it), otherwise the messages are
lost.

## `CSV file not found`

The message lists the CSV files that *are* present at that location and the
working directory. The usual cause is that `COLLES_CSV_PATH` is a path **inside
the container**:

```
COLLES_CSV_PATH=input/colles.csv          # /app/input/colles.csv
COLLES_CSV_PATH=/app/input/colles.csv     # same file
COLLES_CSV_PATH=./input/colles.csv        # also fine
```

With the provided `docker-compose.yml`, `./input` on your machine is mounted at
`/app/input`, so the file must be at `./input/colles.csv` **next to**
`docker-compose.yml`. If you changed the volume, change the setting to match.

## `exists but cannot be read`

The file is mounted read-only but is not readable by the container user:

```
chmod a+r input/colles.csv
```

## `is not valid UTF-8 text`

The export was saved in another encoding, typically Excel's "CSV UTF-16" or an
"ANSI" (Latin-1) file. Re-export it as **CSV UTF-8**. The message says so
explicitly when it recognises a UTF-16 byte-order mark.

## `missing column(s) ...`

The header does not contain the columns the tool needs. It must be comma
separated with at least `Date`, `Matière`, `Colleur`, `Salle` and `Début`, see
[CSV format](csv.md). A semicolon-separated export is **not** accepted: open it
in a spreadsheet and save it as comma separated.

## The container tries to log in to ecolle

It found no CSV file and fell back to the pre-2.0.0 scraper. Set

```
DISABLE_ECOLLE_FETCH=true
```

to make the CSV file the only source, so a mistake in the path is reported
immediately instead of turning into a scrape attempt.

## `unknown field 'xxx'`

`NTFY_FORMAT` names a field that does not exist. The error message lists every
usable field, see [the field tables](configuration.md#ntfy_format).

## TLS errors

* Notifications to a self-hosted ntfy over a self-signed certificate:

      SELF_SIGNED_CERTIFICATE=true
      # or, preferably:
      ROOT_CA_PATH=/app/certs/rootCA.pem

  `ROOT_CA_PATH` is only used when the certificate itself is not trusted by the
  system. The `certs` volume in `docker-compose.yml` is commented out by
  default: uncomment it if you need it.

* The same two settings are used for the scraper fallback connection to ecolle.

## Exit codes

| Code | Meaning                                                              |
| ---- | -------------------------------------------------------------------- |
| `0`  | The run completed. This includes "there was no upcoming colle".        |
| `1`  | The agenda could not be built, or a notification could not be sent.    |

A non-zero exit code is meant to make cron and systemd report a failure, so
silence is never mistaken for success.

## Still stuck?

Run the tool by hand with the container's own environment to see what it does:

```
docker compose run --rm app
```

The first lines always say which CSV file was read, how many colles were parsed
and which ones were selected. Those three lines identify almost every problem.

Please [open an issue](https://github.com/florianzarbo/ecolle-scraper/issues)
with that output (remove your topic name first).
