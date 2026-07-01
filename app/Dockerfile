FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# environment variables for uv to work
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# install production dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --group prod

# copy code files
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group prod

# slim image for execution 
FROM python:3.11-slim-bookworm AS runtime

# run as an unprivileged user.
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

# set python PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 8000

CMD ["gunicorn", "api.main:app", "-c", "gunicorn.conf.py"]
