# Wslny API (Gateway + Orchestrator)

The Wslny API is the public backend gateway for the platform. It is responsible for authentication, request validation, service orchestration, persistence, and admin analytics.

## Role In The System

- Exposes HTTP/JSON endpoints to web/mobile clients.
- Enforces JWT security and role-based access.
- Orchestrates internal gRPC calls to AI and RoutingEngine.
- Persists route history and serves admin statistics.

This is the control plane of the platform. Frontends must call this service only.

## Communication Pattern

```text
Client -> Wslny API -> (optional) Ai-Service -> RoutingEngine -> Wslny API -> Client
                 |
                 \-> PostgreSQL (users, history, analytics)
```

## Flow Logic

### Text input

1. Receive `POST /api/route` with `text`.
2. Call AI gRPC `ExtractRoute` to get source/destination coordinates.
3. Call Routing gRPC `GetRoute` with coordinates.
4. Return standardized JSON and persist history.

### Map-pin input

1. Receive `POST /api/route` with coordinates.
2. Skip AI service.
3. Call Routing gRPC directly.
4. Return standardized JSON and persist history.

## Important Endpoints

- Auth:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/google-login`
  - `GET /api/auth/profile`
- Routing:
  - `POST /api/route` (JWT required)
- Admin:
  - `POST /api/admin/change-role`
  - `GET /api/admin/users`
  - `GET /api/admin/analytics/routes/overview`
  - `GET /api/admin/analytics/routes/top-routes`
- API docs:
  - `GET /api/schema/`
  - `GET /api/docs/`

## Why This Is Important

- Keeps frontend simple and secure (single domain + auth boundary).
- Prevents AI-to-Routing service chaining anti-pattern.
- Allows efficient bypass path for map-pin requests.
- Enables governance and observability (history + analytics) in one place.

## Runtime Service Folder

Operational Django project and Docker runtime files are in `API/Wslny`.
See `API/Wslny/README.md` for startup details.
