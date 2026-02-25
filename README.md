# Wslny - Microservices Transportation Platform

Wslny is a multi-service transportation platform for Greater Cairo. It combines user-facing APIs, Arabic NLP location interpretation, and high-performance route computation into a single orchestrated system.

## Services

- `API/Wslny` (Django + DRF): Public entrypoint, authentication, orchestration, history, admin analytics.
- `Ai-Service` (Python + gRPC): Extracts origin/destination from natural language and geocodes to coordinates.
- `RoutingEngine` (C++ + gRPC): Computes the best path from coordinates using A* over GTFS data.

## Why This Architecture

- **Single entrypoint**: Frontend only calls Wslny API, so auth, validation, and security are centralized.
- **Separation of concerns**: AI does NLP/geocoding only; RoutingEngine does routing only.
- **Lower latency**: Internal communication uses gRPC/Protobuf over HTTP/2.
- **Flexible flows**: Text requests call AI then routing; map-pin requests bypass AI and go directly to routing.

## End-to-End Communication

```text
Client (Web/Mobile)
    |
    | HTTP/JSON + JWT
    v
Wslny API (Orchestrator)
    |\
    | \-- gRPC --> Ai-Service (text flow only)
    |
    \---- gRPC --> RoutingEngine (text + map flows)
            |
            \--> GTFS graph loaded in-memory from RoutingEngine/Database

Wslny API --> PostgreSQL (users, route history, analytics)
```

## Request Flows

### 1) Text Flow

`POST /api/route` with:

```json
{
  "text": "عايز اروح العباسيه من مسكن",
  "filter": "optimal"
}
```

Pipeline:

1. Wslny validates JWT and payload.
2. Wslny calls AI gRPC `TransitInterpreter.ExtractRoute`.
3. AI returns names + lat/lon for destination and, when available, origin.
4. If origin is missing, API can use `current_location` from client payload.
5. Wslny calls RoutingEngine gRPC `RoutingService.GetRoute`.
6. Wslny filters to a single route by `filter` (`optimal`, `fastest`, `cheapest`, `bus_only`, `microbus_only`, `metro_only`).
7. Wslny returns final JSON route response with one `route` object.
8. Wslny stores route history + latency metrics.

### 2) Map-Pin Flow

`POST /api/route` with:

```json
{
  "origin": { "lat": 30.0539, "lon": 31.2383 },
  "destination": { "lat": 30.0735, "lon": 31.2823 },
  "filter": "cheapest"
}
```

Pipeline:

1. Wslny validates JWT and coordinates.
2. Wslny bypasses AI.
3. Wslny calls RoutingEngine directly.
4. Wslny filters to one route by `filter`.
5. Wslny returns final JSON route response.
6. Wslny stores route history + latency metrics.

## Main API Surfaces

- Auth: `/api/auth/register`, `/api/auth/login`, `/api/auth/google-login`, `/api/auth/profile`
- Routing: `/api/route`
- Route history: `/api/route/history`
- Admin analytics:
  - `/api/admin/analytics/routes/overview`
  - `/api/admin/analytics/routes/top-routes`
  - `/api/admin/analytics/routes/filters`
  - `/api/admin/analytics/routes/unresolved`
- OpenAPI:
  - `/api/schema/`
  - `/api/docs/`

## Documentation Per Service

- API gateway/orchestrator docs: `API/README.md`
- Wslny runtime service docs: `API/Wslny/README.md`
- AI service docs: `Ai-Service/README.md`
- Routing engine docs: `RoutingEngine/README.md`

## Running The Stack

From repository root:

```bash
docker compose up --build
```

Required environment variables:

- `GOOGLE_MAPS_API_KEY` for geocoding in AI service.

## Operational Importance

- **Correctness**: All route decisions happen from real coordinates.
- **Scalability**: AI and routing can scale independently.
- **Observability**: Route history records success/failure and latencies for each request.
- **Admin intelligence**: Analytics endpoints are built from persisted history.
