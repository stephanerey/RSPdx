# API### <API Area / Service>

> **PRD Policy:** **LOCKED (template)** — Do **not** edit this file in a project PRD. If you need project-specific changes, **copy** it to a new file and reference it from `PRD.md`.


**Phase:** PXX  
**Status:** Draft  
**Owner:** <name>  
**Last updated:** YYYY-MM-DD

## Goal
<...>

## Endpoint
- Method: <GET/POST/...>
- Path: `/...`
- Auth: <none/bearer/session/etc.>

## Request
### Headers
- <...>

### Body (example)
```json
{
  "example": "value"
}
```

## Response
### 200 OK (example)
```json
{
  "result": "ok"
}
```

## Error responses
- 400: <...>
- 401: <...>
- 403: <...>
- 404: <...>
- 500: <...>

## Constraints
- <rate limits, timeouts, payload sizes>

## Acceptance criteria
- <...>

## Testing notes
- <curl examples, contract tests>
