import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from app.errors import http_exception_handler, validation_exception_handler
from starlette.requests import Request


@pytest.mark.asyncio
async def test_http_exception_handler_returns_error_shape():
    scope = {"type": "http"}
    request = Request(scope)
    exc = HTTPException(status_code=409, detail={"code": "DUPLICATE", "message": "dup"})
    resp = await http_exception_handler(request, exc)
    assert resp.status_code == 409
    import json as _json
    body = _json.loads(resp.body)
    assert body["success"] is False
    assert body["error"]["code"] == "DUPLICATE"


@pytest.mark.asyncio
async def test_http_exception_handler_with_string_detail_and_meta_from_state():
    scope = {"type": "http"}
    request = Request(scope)
    # set state values
    request.state.request_id = "req123"
    request.state.correlation_id = "corr123"
    exc = HTTPException(status_code=400, detail="bad request")
    resp = await http_exception_handler(request, exc)
    assert resp.status_code == 400
    import json as _json
    body = _json.loads(resp.body)
    assert body["error"]["code"] == "ERROR"
    assert body["meta"]["request_id"] == "req123"
    assert body["meta"]["correlation_id"] == "corr123"


@pytest.mark.asyncio
async def test_validation_exception_handler_builds_details():
    scope = {"type": "http"}
    request = Request(scope)
    exc = RequestValidationError(errors=[{"loc": ("body", "field"), "msg": "invalid", "type": "value_error"}], body={})
    resp = await validation_exception_handler(request, exc)
    assert resp.status_code == 422
    import json as _json
    body = _json.loads(resp.body)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "field" in body["error"]["details"]
