# Wslny Runtime Service

This folder contains the runnable Django service for Wslny API.

## Responsibilities

- HTTP API for authentication, routing, and admin features.
- gRPC clients for `Ai-Service` and `RoutingEngine`.
- Route orchestration logic for text and map modes.
- Route history persistence for analytics.
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
- `src/Presentation/views/admin_views.py`: analytics APIs.
- `src/Presentation/settings.py`: JWT, gRPC targets, OpenAPI config.

## Environment Variables

- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `AI_GRPC_HOST`, `AI_GRPC_PORT`, `AI_GRPC_TIMEOUT_SECONDS`
- `ROUTING_GRPC_HOST`, `ROUTING_GRPC_PORT`, `ROUTING_GRPC_TIMEOUT_SECONDS`

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
