import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.orchards.router import router as trees_router
from api.orchards.service import SurveyNotFoundError

# construct app
app = FastAPI(title="api", version="0.1.0")

# register orchards router
app.include_router(trees_router)


def _error(status_code: int, message: str) -> JSONResponse:
    """Uniform error envelope: always ``{"error": "<message>"}``."""
    return JSONResponse(status_code=status_code, content={"error": message})


@app.exception_handler(SurveyNotFoundError)
async def handle_survey_not_found(request: Request, exc: SurveyNotFoundError):
    return _error(404, str(exc))


@app.exception_handler(httpx.HTTPStatusError)
async def handle_upstream_status_error(request: Request, exc: httpx.HTTPStatusError):
    # The Aerobotics API returned a non-2xx response (e.g. bad token, 5xx).
    logger.warning("Upstream returned {}: {}", exc.response.status_code, exc)
    return _error(502, f"upstream request failed: {exc}")


@app.exception_handler(httpx.RequestError)
async def handle_upstream_request_error(request: Request, exc: httpx.RequestError):
    # Could not reach the Aerobotics API at all (timeout, DNS, connection).
    logger.warning("Upstream request error: {}", exc)
    return _error(502, f"could not reach upstream service: {exc}")


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    # e.g. a non-integer orchard_id in the path.
    return _error(422, f"invalid request: {exc.errors()}")


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, str(exc.detail))


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    # Catch-all for anything not handled above (bad tree data, detector /
    # numpy / utm failures on degenerate input, etc). Log the full detail
    # server-side; return the message to the caller.
    logger.exception("Unhandled error processing {}", request.url.path)
    return _error(500, str(exc))


@app.get("/ping")
def ping():
    """Simple test endpoint to verify the server is running."""
    return {"status": "ok", "message": "pong"}
