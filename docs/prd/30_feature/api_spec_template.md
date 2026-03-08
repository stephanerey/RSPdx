# API### <API Area / Service>

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Phase:** PXX  
**Status:** Draft  
**Owner:** <name>  
**Last updated:** YYYY-MM-DD

## Goal
<...>

## Requirement refs
- `REQ-###`

## Endpoint
- Method: <GET/POST/...>
- Path: `/...`
- Auth: <none/bearer/session/etc.>
- Versioning: <...>
- Idempotency: <...>

## Request
### Headers
- <...>

### Parameters
- <...>

### Body (example)
```json
{
  "example": "value"
}
```

## Response
### Success example
```json
{
  "result": "ok"
}
```

## Error responses
- `400`: <...>
- `401`: <...>
- `403`: <...>
- `404`: <...>
- `409`: <...>
- `422`: <...>
- `500`: <...>

## Constraints
- Rate limits:
- Timeouts:
- Payload size:
- Ordering / retry behavior:

## Observability
- Logs:
- Metrics:
- Trace / request ID:

## Acceptance criteria
- <...>

## Testing notes
- Contract tests:
- Integration tests:
- Example calls:
- Validation refs: `VAL-###`
