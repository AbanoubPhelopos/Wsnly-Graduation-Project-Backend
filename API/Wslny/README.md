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
- `GET /api/admin/analytics/routes/filters` returns only the top-used filter summary after applying query filters.

## Routing Notes

- `POST /api/route` accepts `filter` enum for both text and map requests: `1=optimal`, `2=fastest`, `3=cheapest`, `4=bus_only`, `5=microbus_only`, `6=metro_only`.
- `POST /api/routes/search` accepts `destination_text`, current location (`current_location` or query params), and `filter`.
- If destination is not found, search returns a suggestion response with `Do you mean ...` and destination coordinates.
- `POST /api/routes/search/confirm` accepts confirmed destination coordinates + current location + `filter`, then returns route.
- `GET /api/routes/metadata` provides filter dictionary, supported modes, query params, and transport methods.
- Response includes one `route` only (not a routes array).
- Fare behavior:
  - metro: tiered by total metro stops
  - bus: `20 EGP` per bus ride segment
  - microbus: `10 EGP` per microbus ride segment

## Client Integration Examples

```bash
curl -X GET "http://localhost:8000/api/routes/metadata" \
  -H "Authorization: Bearer <jwt_token>"
```

```bash
curl -X POST "http://localhost:8000/api/routes/search" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "destination_text": "العباسية",
    "current_location": {"lat": 30.1189, "lon": 31.3400},
    "filter": 1
  }'
```

```bash
curl -X POST "http://localhost:8000/api/routes/search/confirm" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_location": {"lat": 30.1189, "lon": 31.3400},
    "destination": {"name": "العباسية", "lat": 30.0728, "lon": 31.2841},
    "filter": 1
  }'
```
