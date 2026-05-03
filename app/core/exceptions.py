from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette import status
import logging

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error({
        "event": "HTTP Exception",
        "path": request.url.path,
        "detail": exc.detail,
        "status_code": exc.status_code
    })

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    logger.critical({
        "event": "Unhandled Exception",
        "path": request.url.path,
        "error": str(exc)
    })

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error"
        }
    )