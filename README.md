You need to have uv installed

Debian based :
sudo apt install uv

Arch based :
sudo pacman -S uv

cp .env.example .env

Set the needed variables

uv sync

uv run parse.py
