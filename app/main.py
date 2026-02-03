from fastapi import FastAPI, Request
from app.routers import vehicles, drivers, assignments
from app import errors
import uuid

app = FastAPI()

# Simple middleware to attach request_id and correlation_id per request
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = str(uuid.uuid4())
    request.state.request_id = rid
    request.state.correlation_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response

# Register custom exception handlers
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException

app.add_exception_handler(Exception, errors.generic_exception_handler)
app.add_exception_handler(RequestValidationError, errors.validation_exception_handler)
app.add_exception_handler(HTTPException, errors.http_exception_handler)

app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(assignments.router)
