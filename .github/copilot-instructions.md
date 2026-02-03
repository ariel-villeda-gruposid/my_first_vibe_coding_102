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
- plate_number: string (unique)
- model: string
- year: integer
- type: enum (SEDAN, SUV, TRUCK, VAN)
- fuel_type: enum (GASOLINE, DIESEL, ELECTRIC, HYBRID)
- status: enum (ACTIVE, INACTIVE, MAINTENANCE)
- created_at: datetime (UTC)

Rules:
- Plate number must be unique
- INACTIVE or MAINTENANCE vehicles cannot be assigned

---

#### Driver
Represents a person authorized to operate vehicles.

Attributes:
- id: UUID (string)
- name: string
- license_number: string (unique)
- contact_number: string
- status: enum (ACTIVE, SUSPENDED)
- created_at: datetime (UTC)

Rules:
- SUSPENDED drivers cannot receive assignments

---

#### Assignment
Represents a relationship between a driver and a vehicle for a time period.

Attributes:
- id: UUID (string)
- driver_id: UUID
- vehicle_id: UUID
- start_date: date
- end_date: date | null
- created_at: datetime (UTC)

Rules:
- A driver can only have one active assignment at a time
- A vehicle can only have one active assignment at a time
- start_date must be <= end_date
- Foreign keys must exist and be valid

---

## API Design Principles

- RESTful endpoints
- Resource-oriented URLs
- Stateless operations
- Clear validation errors
- Distinct layers for controllers, services, and data access
- **Pagination**: Large collections support `limit` and `skip` query parameters (MongoDB style)
- **Filtering**: Resources support filtering via query parameters (status, type, etc.)
- **Sorting**: Default sort by creation date (createdAt) descending
- **Error Handling**: Standardized error response format with error codes
- **Date Format**: All dates use ISO 8601 format (YYYY-MM-DD for date fields)
- **ObjectId Format**: MongoDB ObjectId represented as string in JSON responses
- **Type Validation**: Pydantic v2 schema validation on all requests


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
    "request_id": "req_xyz123"
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
    "request_id": "req_xyz123"
  }
}
```

### Error Handling

- 400: Validation errors
- 404: Resource not found
- 409: Business rule conflict (e.g. already assigned)
- 500: Server error
- 503: Service temporarily unavailable

Error format:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  },
  "meta": {
    "timestamp": "2026-01-28T10:30:00Z",
    "request_id": "req_xyz123"
  }
}
```

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
