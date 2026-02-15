
# ntfy Notifications from Ecolle

This project enables sending ntfy notifications to a specific topic and server using your "colles" from an Ecolle instance.

Full documentation [here](https://florianzarbo.github.io/ecolle-scraper/)

## Prerequisites
- **uv** (Python package manager) must be installed.

### Installation
**Debian-based systems:**
```bash
sudo apt install uv
```

**Arch Linux:**
```bash
sudo pacman -S uv
```

## Quick Start
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set the required variables (e.g., Ecolle credentials, ntfy server/topic).

3. Install dependencies:
   ```bash
   uv sync
   ```

4. Run the application:
   ```bash
   uv run main.py
   ```