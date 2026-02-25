# Wslny Runtime Service

This folder contains the runnable Django service for Wslny API.

## Responsibilities

- HTTP API for authentication, routing, and admin features.
- gRPC clients for `Ai-Service` and `RoutingEngine`.
- Route orchestration logic for text and map modes.
- Route history persistence for analytics.
- Route filter selection and fare estimation.
- User route history endpoint.
- OpenAPI/Swagger documentation.

## Communication Design

```text
HTTP Client
   |
   v
RouteOrchestratorView (Django)
   |---- gRPC ----> Ai-Service (text only)
   |---- gRPC ----> RoutingEngine (text + map)
   |
   +---- PostgreSQL (route history + users)
```

## Key Files

- `src/Presentation/views/orchestrator.py`: text/map orchestration and error mapping.
- `src/Infrastructure/GrpcClients/`: AI and routing gRPC adapters.
- `src/Infrastructure/History/models.py`: persisted route history.
- `src/Infrastructure/History/migrations/0002_routehistory_preference_and_selection_fields.py`: request and analytics metadata fields.
- `src/Infrastructure/History/migrations/0003_backfill_has_result_for_existing_rows.py`: historical data backfill for analytics quality.
- `src/Presentation/views/admin_views.py`: analytics APIs.
- `src/Presentation/settings.py`: JWT, gRPC targets, OpenAPI config.

## Environment Variables

- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `AI_GRPC_HOST`, `AI_GRPC_PORT`, `AI_GRPC_TIMEOUT_SECONDS`
- `ROUTING_GRPC_HOST`, `ROUTING_GRPC_PORT`, `ROUTING_GRPC_TIMEOUT_SECONDS`
- `FARE_BUS_FIXED`
- `FARE_METRO_UP_TO_9`, `FARE_METRO_UP_TO_16`, `FARE_METRO_UP_TO_23`, `FARE_METRO_ABOVE_23`
- `FARE_TRANSFER_PENALTY`
- `ROUTE_LONG_WALK_THRESHOLD_METERS`

## Local/Container Startup

From repository root (recommended):

```bash
docker compose up --build
```

Or run API only from this folder after dependencies + database are ready:

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## API Docs

- Schema: `/api/schema/`
- Swagger UI: `/api/docs/`

Use `Bearer <jwt_token>` in Swagger Authorize to test protected endpoints.

## Admin Analytics

- Generic analytics endpoint: `GET /api/admin/analytics/routes/query`
- Supports reusable filters (`source`, `status`, `filter`, `from_date`, `to_date`) and
  composable query options (`metrics`, `group_by`, `sort`, `order`, `limit`, `offset`).
- Returns consistent metadata (`meta`) and validates invalid analytics query options
  with `400 INVALID_ANALYTICS_QUERY` details.

## Routing Notes

- `POST /api/route` accepts `filter` enum for both text and map requests: `1=optimal`, `2=fastest`, `3=cheapest`, `4=bus_only`, `5=microbus_only`, `6=metro_only`.
- `POST /api/routes/search` is a client-friendly alias of `POST /api/route`.
- `POST /api/routes/batch` processes multiple route requests in one call (`requests[]`, max 20).
- Text requests may include `current_location` for destination-only phrases.
- Text requests may also pass optional query params `current_latitude` and `current_longitude` (nullable) as fallback current location.
- `GET /api/routes/metadata` provides filter dictionary, supported modes, query params, and transport methods.
- `POST /api/routes/validate` validates request payloads without calling upstream AI/routing services.
- Response includes one `route` only (not a routes array).
- Fare behavior:
  - metro: tiered by total metro stops
  - bus: `20 EGP` per bus ride segment
  - microbus: `10 EGP` per microbus ride segment
