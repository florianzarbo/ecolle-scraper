# ntfy Notifications from Ecolle


## Prerequisites

 - __uv__ (Python package manager) must be installed.

### Installation

#### Debian-based systems:

    sudo apt install uv

#### Arch-based systems:

    sudo pacman -S uv

## Quick Start

1. Copy the example environment file:

        cp .env.example .env

2. Edit .env and set the required variables.
See [Configuration](configuration.md).

3. Install dependencies:

        uv sync

4. Run the application:

        uv run main.py
