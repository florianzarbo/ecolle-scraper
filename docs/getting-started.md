# ntfy Notifications from Ecolle



### Docker compose (recommended)
1. Install __[docker](https://docs.docker.com/get-started/get-docker/)__
2. Copy [docker-compose.yml](docker-compose.yml)
3. Edit required variables
4. `docker compose up -d`

### Native
1. Install __[uv](https://docs.astral.sh/uv/getting-started/installation/)__
2. `git clone https://github.com/florianzarbo/ecolle-scraper.git`
3. Edit `.env`, see [configuration](configuration.md)
4. `uv run main.py`
