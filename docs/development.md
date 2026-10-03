# Development

## Layout

| File | Role |
| ---- | ---- |
| `main.py` | entry point: build the agenda, select the colles, notify |
| `fetch.py` | reads the CSV export (and the legacy scraper fallback), writes the normalised agenda |
| `parse.py` | reads the normalised agenda and selects the upcoming colles |
| `notif.py` | builds the message and posts it to ntfy |
| `config.py` | every environment variable, read in one place |
| `dates.py` | French date and time parsing and formatting |
| `tests/` | the test suite (not copied into the image) |

The flow is one-directional:

```
CSV export ──fetch──▶ output/agenda.csv ──parse──▶ rows ──notif──▶ ntfy
```

`fetch.py` normalises whatever the source is into the same row shape, so
`parse.py` and `notif.py` never need to know whether the colles came from a CSV
file or from a scrape.

## Running the tests

```
uv run python -m unittest discover -s tests
```

Or, with the environment already installed:

```
python -m unittest discover -s tests
```

They need nothing but the standard library, so they run anywhere. There are
around 130 of them, grouped by module:

| File | Covers |
| ---- | ------ |
| `tests/test_dates.py` | date and time parsing, French names, year inference |
| `tests/test_fetch.py` | the CSV reader, its errors, and the scraper fallback |
| `tests/test_parse.py` | selecting the upcoming colles |
| `tests/test_notif.py` | the message format and its fields |

`tests/helpers.py` gives each test its own temporary directory and restores the
environment afterwards, so the order of the tests cannot matter.

### A note on the environment

Every setting is read through `config.setting()` when it is needed, never at
import time. That is what allows a test to change a variable and see the effect
without reloading a module, and it means a `.env` file loaded later still takes
effect. Please keep it that way when adding settings.

## Building the image

```
docker build -t ecolle-scraper .
docker run --rm -v "$PWD/input:/app/input:ro" -e NTFY_TOPIC=test \
  -e DISABLE_ECOLLE_FETCH=true ecolle-scraper
```

The image is a two-stage build: the dependencies are resolved with `uv` into a
virtual environment, then copied into a clean runtime image. `uv sync --frozen`
means a change to `pyproject.toml` without a matching `uv.lock` fails the
build, so run `uv lock` after editing the dependencies.

The container sets `TZ=Europe/Paris`, because the colles are announced in local
time and a UTC container would disagree with the host about which colles are
still to come. Override `TZ` if you are in another timezone.

## Documentation

The documentation is built with MkDocs:

```
uv tool run --from mkdocs-material mkdocs serve      # live preview
uv tool run --from mkdocs-material mkdocs build --strict
uv tool run --from mkdocs-material mkdocs gh-deploy --ignore-version
```

`--ignore-version` is needed because the deployed branch records the MkDocs
version that produced it, and it refuses to deploy with an older one.

`gh-pages` is rewritten on every deploy, so it always needs a force push; the
GitHub mirror picks the branch up automatically. A workflow also runs the tests
on every push, see `.github/workflows/`.
