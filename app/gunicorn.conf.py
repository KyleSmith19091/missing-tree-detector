"""Gunicorn config for the FastAPI (ASGI) app.

Run with:  uv run gunicorn api.main:app -c gunicorn.conf.py
"""
import multiprocessing

# ASGI worker — required for FastAPI. Plain gunicorn sync workers cannot
# serve an ASGI app.
worker_class = "uvicorn.workers.UvicornWorker"

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
