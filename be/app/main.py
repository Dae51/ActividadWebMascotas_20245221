import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .errors import ApiError
from .routers import adoptions, auth, notifications, pets, ws


logger = logging.getLogger("pawshome.api")

app = FastAPI(title="PawsHome API", version="1.0.0")


def error_body(message: str, code: str, errors: list[dict] | None = None) -> dict:
    payload = {
        "detail": message,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if errors is not None:
        payload["error"]["errors"] = errors
    return payload


@app.exception_handler(ApiError)
async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.detail, exc.code, exc.errors),
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, str):
        message = exc.detail
        errors = None
    else:
        message = "Request failed"
        errors = exc.detail if isinstance(exc.detail, list) else None

    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(message, f"http_{exc.status_code}", errors),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body("Validation error", "validation_error", exc.errors()),
    )


@app.exception_handler(DataError)
async def handle_data_error(_: Request, __: DataError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("Invalid data for the requested operation", "invalid_data"),
    )


@app.exception_handler(IntegrityError)
async def handle_integrity_error(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=error_body("Database conflict", "database_conflict"),
    )


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(_: Request, __: SQLAlchemyError) -> JSONResponse:
    logger.exception("Unhandled database error")
    return JSONResponse(
        status_code=503,
        content=error_body("Database is not available", "database_unavailable"),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return JSONResponse(
        status_code=500,
        content=error_body("Internal server error", "internal_server_error"),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(pets.router)
app.include_router(adoptions.router)
app.include_router(notifications.router)
app.include_router(ws.router)


@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "version": app.version}
