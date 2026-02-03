import uuid
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


def make_meta(request: Request):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    correlation_id = getattr(request.state, "correlation_id", request_id)
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "request_id": request_id, "correlation_id": correlation_id}


async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "ERROR")
        message = detail.get("message", str(detail))
        details = detail.get("details", {})
    else:
        code = "ERROR"
        message = str(detail)
        details = {}
    payload = {"success": False, "error": {"code": code, "message": message, "details": details}, "meta": make_meta(request)}
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Build per-field details
    details = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        field = loc[-1] if loc else "_".join(str(x) for x in loc)
        details.setdefault(field, []).append({"code": "VALIDATION_ERROR", "message": err.get("msg")})
    payload = {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Validation error", "details": details}, "meta": make_meta(request)}
    return JSONResponse(status_code=422, content=payload)


async def generic_exception_handler(request: Request, exc: Exception):
    payload = {"success": False, "error": {"code": "SERVER_ERROR", "message": "Internal server error"}, "meta": make_meta(request)}
    return JSONResponse(status_code=500, content=payload)
