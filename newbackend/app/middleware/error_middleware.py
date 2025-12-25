"""
Error Handling Middleware
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.utils.response import R
import logging

logger = logging.getLogger(__name__)


def add_error_middleware(app: FastAPI):
    """Add error handling middleware to the application"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return R.error(
            msg=exc.detail,
            code=exc.status_code
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return R.error(
            msg="Validation Error",
            code=422,
            data={"details": exc.errors()}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return R.error(
            msg="Internal Server Error",
            code=500
        )