---
name: fleet-management-api
description: >
  Fleet Management API for managing Vehicles, Drivers, and Assignments.
  Use this skill when designing models, endpoints, validations, or tests.
  Development follows strict TDD using the Interview-Driven methodology.
---

# Fleet Management API – Copilot Skill File

## Purpose
This skill guides Copilot to assist in building a Fleet Management REST API
using **Interview-Driven Test-Driven Development (ID-TDD)**.

Copilot MUST:
- Start from functional behavior
- Ask or infer requirements before implementation
- Write tests first
- Implement only what is required to satisfy failing tests

---

## Core Domain

## TECHNICAL REQUIREMENTS
- Use Python 3.11+
- Use FastAPI for the web framework
- MongoDB NoSQL Database
- docker-compose for local development
- Use Pydantic for data validation
- Follow RESTful API design principles

## Coding Standards
- **PEP 8 Compliance**: All Python code must follow PEP 8 style guidelines
- **Type Hints**: Required for all function parameters and return types
- **Docstrings**: Mandatory for all modules, classes, and functions using Google-style format

### Entities

#### Vehicle
Represents a fleet vehicle.

Attributes:
- id: UUID (string)
- plate_number: string (unique, alphanumeric, no whitespace, max length 10)
- model: string
- year: integer (>= 1996)
- type: enum (SEDAN, SUV, TRUCK, VAN)
- fuel_type: enum (GASOLINE, DIESEL, ELECTRIC, HYBRID)
- status: enum (ACTIVE, INACTIVE, MAINTENANCE)
- created_at: datetime (UTC, auto-generated)
- updated_at: datetime (UTC, auto-generated on create and set to current UTC on every update)

Rules:
- Plate number must be unique (case-insensitive, whitespace-trimmed) and stored normalized (uppercase).
- `plate_number` must be alphanumeric with no whitespace and length <= 10. Leading/trailing whitespace must be trimmed on all string attributes.
- INACTIVE or MAINTENANCE vehicles cannot be assigned. To change to INACTIVE or MAINTENANCE, a vehicle must have no active assignments; assigned vehicles must be unassigned first.
- Only soft deletes are permitted. Deletion is allowed only when the vehicle is not assigned. Reusing a plate requires reactivating the existing soft-deleted vehicle record and updating other fields instead of creating a new record.
- Partial updates must not set omitted required fields to null.
- `updated_at` is auto-generated on create and set to current UTC on every update.
- Concurrency conflicts are detected using `ETag` / `If-Match` and return `409 CONCURRENCY_CONFLICT` on mismatch.

---

#### Driver
Represents a person authorized to operate vehicles.

Attributes:
- id: UUID (string)
- name: string
- license_number: string (unique, alphanumeric)
- contact_number: string (validated phone number format)
- status: enum (ACTIVE, SUSPENDED)
- created_at: datetime (UTC, auto-generated)
- updated_at: datetime (UTC, auto-generated on create and set to current UTC on every update)

Rules:
- SUSPENDED drivers cannot receive assignments.
- `license_number` must be unique (case-insensitive, whitespace-trimmed) and alphanumeric. Reuse of a `license_number` must reactivate the existing deactivated driver record instead of creating a new one.
- Trim leading/trailing whitespace on all string attributes; store normalized values when applicable.
- To suspend or soft-delete a driver, they must have no active assignments; attempts to do so must return `409 DRIVER_HAS_ACTIVE_ASSIGNMENTS`.
- `contact_number` must pass phone number validation and be returned as part of validation details on failure (422).
- Partial updates must not set omitted required fields to null.
- Only soft deletes are permitted.
- Concurrency conflicts are detected using `ETag` / `If-Match` and return `409 CONCURRENCY_CONFLICT` on mismatch.
---

#### Assignment
Represents a relationship between a driver and a vehicle for a time period.

Attributes:
- id: UUID (string)
- driver_id: UUID
- vehicle_id: UUID
- start_datetime: datetime (UTC)
- end_datetime: datetime (UTC) | null
- notes: string | null (max 127 characters after trimming trailing whitespace)
- created_at: datetime (UTC, auto-generated)
- updated_at: datetime (UTC, auto-generated on create and set to current UTC on every update)

Rules:
- A driver can only have one active assignment at a time.
- A vehicle can only have one active assignment at a time.
- POST requests must validate `start_datetime <= end_datetime` when `end_datetime` is provided; `end_datetime` may be null for ongoing assignments.
- Foreign keys (`driver_id`, `vehicle_id`) must exist and be valid (404 `DRIVER_NOT_FOUND` / `VEHICLE_NOT_FOUND`).
- Reassigning the same driver and vehicle again must create a new Assignment record (do not reuse old ones). Checking that there is no active assignment is sufficient (active = `end_datetime` is null or >= now).
- `end_datetime` indicates a closed assignment and must be set to close an active assignment.
- If a vehicle or driver is set to INACTIVE or SUSPENDED respectively, any active assignments must be auto-closed (set `end_datetime = now`) by the service that changed the status.
- `end_datetime` can be updated only if the related driver and vehicle remain ACTIVE and the update does not create overlapping assignments for the same driver or vehicle.
- On update, only `notes` and `end_datetime` may be modified; `start_datetime` can be modified only if the new `start_datetime` is <= now.
- On update, validate `end_datetime >= start_datetime` only if `end_datetime` is not null.
- Creating or updating an assignment with a SUSPENDED driver or INACTIVE/MAINTENANCE vehicle is disallowed (`409 DRIVER_SUSPENDED` / `VEHICLE_INACTIVE`).
- Attempting to delete an active assignment will auto-close it (set `end_datetime = now`) and then return `204 No Content` if successful; otherwise return `409` with the appropriate error code.
- `notes` must be trimmed for trailing whitespace and be <= 127 characters; otherwise return `422 VALIDATION_ERROR` with per-field details.
---

## API Design Principles

- RESTful endpoints
- Resource-oriented URLs (versioned under `/api/v1/`)
- Stateless operations
- Clear validation errors with per-field details
- Distinct layers for controllers, services, and data access
- **Pagination**: Large collections support `limit` and `skip` query parameters (MongoDB style). Default `limit` = 50, maximum `limit` = 500.
- **Filtering**: Resources support filtering via query parameters (status, type, etc.). Soft-deleted resources are excluded by default; include them with `?include_deleted=true`.
- **Sorting**: Default sort by `updated_at` descending. Allowed sort fields include `updated_at`, `created_at` (all resources) and `start_datetime`, `end_datetime` for assignments.
- **Error Handling**: Standardized error response format with error codes and `correlation_id` in `meta`.
- **Date/Time Format**: All datetimes use ISO 8601 format with UTC timezone (e.g., `2026-01-28T10:30:00Z`).
- **ObjectId Format**: MongoDB ObjectId represented as string in JSON responses.
- **Type Validation**: Pydantic v2 schema validation on all requests.


Example endpoints:
- POST /vehicles
- GET /vehicles/{id}
- POST /drivers
- POST /assignments
- DELETE /assignments/{id}

---

## Responses

### Success(2xx)

```json
{
  "success": true,
  "data": {},
  "meta": {
    "timestamp": "2026-01-28T10:30:00Z",
    "request_id": "req_xyz123",
    "correlation_id": "corr_abc123"
  }
}
```

### Pagination Response Format
```json
{
  "success": true,
  "data": [],
  "pagination": {
    "total": 100,
    "limit": 10,
    "skip": 0,
    "has_more": true
  },
  "meta": {
    "timestamp": "2026-01-28T10:30:00Z",
    "request_id": "req_xyz123",
    "correlation_id": "corr_abc123"
  }
}
```

### Error Handling

- 400: Bad Request / Invalid input
- 401: Unauthorized (missing/invalid auth)
- 403: Forbidden (insufficient permissions)
- 404: Resource not found
- 409: Business rule conflict (e.g., already assigned, active assignments)
- 422: Unprocessable Entity (validation errors with per-field `details`)
- 500: Server error
- 503: Service temporarily unavailable

Error format:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "field": [{ "code": "FIELD_CODE", "message": "detail message" }]
    }
  },
  "meta": {
    "timestamp": "2026-01-28T10:30:00Z",
    "request_id": "req_xyz123",
    "correlation_id": "corr_abc123"
  }
}
```
- Use UPPER_SNAKE_CASE for `error.code` (e.g., `VEHICLE_NOT_FOUND`, `DUPLICATE_PLATE`, `DRIVER_HAS_ACTIVE_ASSIGNMENTS`).
- Validation errors should return **422 Unprocessable Entity** and include per-field `details`.
- Do not include stack traces in API responses.

---

## Infrastructure & Operational

- **Authentication**: Bearer JWT (roles/scopes omitted for v1).
- **API Versioning**: URL path versioning using `/api/v1/...` (major-only semantic versions).
- **Concurrency**: Use `ETag` / `If-Match` for conditional updates; on mismatch return `409 CONCURRENCY_CONFLICT`.
- **Soft-delete visibility**: Soft-deleted resources are excluded by default; include them with `?include_deleted=true`.
- **Pagination defaults**: use `limit` + `skip` with default `limit=50` and max `limit=500`. Responses must include `total` and `has_more`.
- **Logging**: Structured JSON logs including `request_id` and `correlation_id`. Default log level `DEBUG` for dev and `INFO` for prod.
- **Rate limiting**: not implemented in-app; to be provided by cloud infrastructure.

---

## Deliverables

- **AI Skill File**: SKILL.md or copilot-instructions.md with project specifications
- **Interview Transcripts**: Saved conversations showing AI questions and your answers for each feature
- **Functional Tests**: tests/functional/ with user-approved tests for all 3 entities (9 tests minimum)
- **Integration Tests**: tests/integration/ with traceability comments to functional tests
- **Unit Tests**: tests/unit/ with traceability comments to functional tests
- **E2E Tests**: tests/e2e/ with real database, min 4 scenarios, traceability comments
- **Traceability Matrix**: Document showing how every test traces to a functional test
- **Coverage Report**: Minimum 90% code coverage with pytest-cov
