from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from bson import ObjectId
from app.routers import vehicles, drivers, assignments
from app import errors
import uuid
import json

# Patch jsonable_encoder to handle ObjectId
from fastapi.encoders import jsonable_encoder as original_jsonable_encoder, ENCODERS_BY_TYPE

original_encoders_by_type = ENCODERS_BY_TYPE.copy()

def patched_jsonable_encoder(obj, **kwargs):
    """Patched jsonable_encoder that handles ObjectId."""
    if isinstance(obj, ObjectId):
        return str(obj)
    return original_jsonable_encoder(obj, **kwargs)

# Apply patch
import fastapi.encoders
fastapi.encoders.jsonable_encoder = patched_jsonable_encoder

# Also patch the ENCODERS_BY_TYPE
ENCODERS_BY_TYPE[ObjectId] = str

def custom_json_serializer(obj):
    """Custom JSON serializer for non-standard types."""
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

# Create FastAPI app
app = FastAPI()

# Custom JSON response class
class MongoJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=custom_json_serializer,
        ).encode("utf-8")

# Override the app to use custom response class
app.default_response_class = MongoJSONResponse

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

