# api

FastAPI server.

## Development

```bash
uv run uvicorn api.main:app --reload
```

Interactive docs at http://127.0.0.1:8000/docs

## Production

Gunicorn manages uvicorn ASGI workers (config in `gunicorn.conf.py`):

```bash
uv sync --group prod
uv run gunicorn api.main:app -c gunicorn.conf.py
```
