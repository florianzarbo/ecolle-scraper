FROM python:3.13-slim-bookworm AS builder
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends locales \
 && sed -i 's/^# *\(fr_FR.UTF-8 UTF-8\)/\1/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

ENV UV_SYSTEM_PYTHON=1 UV_NO_CACHE=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev



FROM python:3.13-slim-bookworm AS runtime
WORKDIR /app

COPY --from=builder /usr/lib/locale/locale-archive /usr/lib/locale/locale-archive
COPY --from=builder /etc/locale.gen /etc/locale.gen

ENV LANG=fr_FR.UTF-8 LANGUAGE=fr_FR:fr LC_ALL=fr_FR.UTF-8
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv
COPY *.py /app/
RUN mkdir -p /app/output

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]