# RoutingEngine (C++ A* Pathfinding)

RoutingEngine is the high-performance C++ gRPC service that computes routes from coordinates.

## Responsibilities

- Load GTFS CSV/TXT data into an in-memory graph at startup.
- Build transit and walking transfer edges.
- Compute candidate routes with A* based search.
- Return structured route steps (duration, type, coordinates).

RoutingEngine does not parse natural language. It only operates on coordinates.

## Communication In The Platform

```text
Wslny API --gRPC GetRoute(origin,destination,mode)--> RoutingEngine
RoutingEngine --gRPC RouteResponse(steps,duration,distance)--> Wslny API
```

Both text and map-pin user requests end up here after orchestration in Wslny API.

## Why This Service Is Critical

- Isolates compute-heavy graph search from web/API concerns.
- Keeps latency low for route computation.
- Supports independent performance tuning and scaling.

## Data Loading And Caching

- Source folder: `RoutingEngine/Database/`.
- Runtime env var: `GTFS_PATH` (defaults internally to `GTFS`, but container sets `/app/Database`).
- Data is loaded once at startup and held in-memory for fast query response.
- Startup now fails fast if no nodes were loaded.

## gRPC Contract

- Service: `RoutingService`
- RPC: `GetRoute(RouteRequest) -> RouteResponse`
- Proto source: `shared/protos/routing.proto`

## Run

Recommended via root compose:

```bash
docker compose up --build
```

Standalone:

```bash
docker build -t routing-engine RoutingEngine
docker run -p 50051:50051 -e GTFS_PATH=/app/Database routing-engine
```

## Internal Flow

1. Parse routes/trips/stops/stop_times from GTFS.
2. Build nodes and weighted edges.
3. Add walking transfer edges between nearby stops.
4. For request coordinates, locate nearby start/end candidates.
5. Run A* variant by mode combinations and return best duration result.
