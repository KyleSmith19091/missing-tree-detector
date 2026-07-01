# syntax=docker/dockerfile:1

# ---- Builder: resolve and install dependencies with uv ----
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Byte-compile installed packages for faster cold starts, and copy (not
# symlink) into the venv so it can be lifted into the runtime image.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (without the project) so this layer is cached
# and only re-runs when the lockfile / pyproject change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --group prod

# Now add the application source and install the project itself.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group prod

# ---- Runtime: slim image with only the venv + app ----
FROM python:3.11-slim-bookworm AS runtime

# Run as an unprivileged user.
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

# Bring over the fully-built virtualenv and application code.
COPY --from=builder --chown=app:app /app /app

# Put the venv's binaries (gunicorn, python) on PATH.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

# gunicorn.conf.py sets the uvicorn worker class, bind (0.0.0.0:8000) and
# worker count. AEROBOTICS_API_TOKEN must be provided at runtime.
CMD ["gunicorn", "api.main:app", "-c", "gunicorn.conf.py"]
