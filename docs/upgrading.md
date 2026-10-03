# Upgrading from 1.x

Version 2.0.0 stopped scraping the ecolle website and started reading a CSV
export instead. If you were running 1.x, here is what changes.

## What changed

| | 1.x | 2.x |
| --- | --- | --- |
| Source of the colles | logged in to ecolle and scraped the agenda page | a CSV file you export yourself |
| `BASE_URL`, `COLLES_USERNAME`, `COLLES_PASSWORD` | required | only used by the scraper fallback, which is off by default |
| `COLLES_CSV_PATH` | did not exist | path of the export, default `input/colles.csv` |
| Container | had to be run on a machine that could reach ecolle | only needs the CSV file |

The old variables are still read, so an existing `.env` does not break. They
are simply no longer needed, and you should remove them so that a typo can no
longer send the tool looking for a website:

```diff
-BASE_URL=https://ecolle.example.com
-COLLES_USERNAME=you
-COLLES_PASSWORD=secret
+COLLES_CSV_PATH=input/colles.csv
+DISABLE_ECOLLE_FETCH=true
```

Leaving them in place is harmless, but if the CSV file is ever missing the tool
will try to scrape instead of telling you the file is missing.

## Steps

1. Export your colles from ecolle as a CSV file, see
   [Getting started](getting-started.md#1-export-your-colles).
2. Put it at `./input/colles.csv`, next to your `docker-compose.yml`.
3. Add the two settings above to `.env`.
4. Make sure the `input` volume is mounted. The 1.x `docker-compose.yml` did not
   have it:

   ```yaml
   volumes:
     - ./input:/app/input:ro
     - ./output:/app/output
   ```

5. Pull the new image and run it:

   ```
   docker compose pull
   docker compose run --rm app
   ```

6. Check the first line of the output says `[*] Reading CSV: input/colles.csv`.
   If it says `[!] No CSV found`, see [Troubleshooting](troubleshooting.md).

## About the notification wording

The default message changed in 2.3.0 to use French dates and times:

```
1.x:  Mathématiques 2026-10-06 16:00 L005 M Jouve
2.x:  mardi 6 octobre 16h00 L005 - Mathématiques (M Jouve)
```

If you had set `NTFY_FORMAT` yourself, your value is still used unchanged. If
you were relying on the old default, either accept the new wording or pin it
explicitly:

```
NTFY_FORMAT={matiere} {date} {heure} {salle} {colleur}
```

## Versions in between

| Version | Change |
| ------- | ------ |
| `2.0.0` | colles read from a CSV export, `pandas` dropped |
| `2.1.0` | `DISABLE_ECOLLE_FETCH`, clearer CSV errors |
| `2.1.1` | `DISABLE_ECOLLE_FETCH` spelling fixed (the misspelt name still works) |
| `2.2.0` | better default notification format |
| `2.3.0` | French dates and times |
| `2.4.0` | one shared date parser, cache no longer lost on a failed scrape, UTF-16 and encoding errors reported, container timezone fixed |

The container image is tagged for each release (`2.4.0`, `2.4`, `2`), so pinning
`ghcr.io/florianzarbo/ecolle-scraper:2.4` avoids a surprise upgrade. `latest`
follows the newest release.
