FROM python:3.12-slim-bookworm AS base

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY ./app/uv.lock ./app/pyproject.toml /app/

RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project --no-dev

COPY ./app/src /app/src

RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM base
COPY --from=builder /app /app
WORKDIR /app

RUN ls -la /app/src
ENV PATH="/app/.venv/bin:$PATH"
# EXPOSE 8000
CMD ["/app/.venv/bin/python", "src/main.py"]