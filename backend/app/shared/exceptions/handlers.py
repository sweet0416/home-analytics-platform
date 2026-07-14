from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": exc.code.value,
                "message": exc.message,
                "details": exc.details,
                "trace_id": getattr(request.state, "trace_id", None),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "code": ErrorCode.validation_error.value,
                "message": "Validation error",
                "details": {"errors": exc.errors()},
                "trace_id": getattr(request.state, "trace_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: {}", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "code": ErrorCode.internal_error.value,
                "message": "Internal server error",
                "details": {},
                "trace_id": getattr(request.state, "trace_id", None),
            },
        )

