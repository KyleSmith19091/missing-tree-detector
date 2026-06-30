from fastapi import FastAPI

app = FastAPI(title="api", version="0.1.0")


@app.get("/ping")
def ping():
    """Simple test endpoint to verify the server is running."""
    return {"status": "ok", "message": "pong"}
