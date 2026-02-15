FROM python:3.12-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends locales \
 && sed -i 's/^# *\(fr_FR.UTF-8 UTF-8\)/\1/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=fr_FR.UTF-8 \
    LANGUAGE=fr_FR:fr \
    LC_ALL=fr_FR.UTF-8

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/  

ENV UV_SYSTEM_PYTHON=1  

WORKDIR /app

COPY *.py /app
COPY .python-version /app/.
COPY pyproject.toml /app/.
COPY uv.lock /app/.

RUN mkdir /app/output

RUN uv sync


ENTRYPOINT ["uv", "run", "main.py"]
