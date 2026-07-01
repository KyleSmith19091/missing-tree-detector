"""Gunicorn config for the FastAPI (ASGI) app.

Run with:  uv run gunicorn api.main:app -c gunicorn.conf.py
"""
import multiprocessing
import os

# ASGI worker — required for FastAPI. Plain gunicorn sync workers cannot
# serve an ASGI app.
worker_class = "uvicorn.workers.UvicornWorker"

bind = f"0.0.0.0:{os.getenv('PORT') or '8000'}"

# WEB_CONCURRENCY lets the deploy environment cap worker count. cpu_count()
# reports the *host* cores inside a container (not the CPU limit), so relying
# on it alone over-spawns memory-heavy numpy/scipy workers on small VMs.
# `or` (not getenv's default) so an empty-string value also falls back.
workers = int(os.getenv("WEB_CONCURRENCY") or multiprocessing.cpu_count() * 2 + 1)
