# 🚂 Routing Engine

A high-performance C++ microservice responsible for multi-modal public transit pathfinding across Greater Cairo's transportation network.

## ⚙️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | C++17 |
| **Build System** | CMake |
| **RPC Framework** | gRPC + Protocol Buffers |
| **Data Source** | GTFS (General Transit Feed Specification) |
| **Containerization** | Docker |

## 🧠 Algorithm — How It Works

The engine solves the **Shortest Path Problem** on a weighted, directed graph built entirely from GTFS public transit data.

### 1. Graph Construction (GTFS Parsing)

On startup, the engine reads five standard GTFS files and constructs an in-memory graph:

| File | Purpose |
|---|---|
| `agency.txt` | Transit agencies operating the routes |
| `routes.txt` | Route definitions (name, type — Bus, Metro, etc.) |
| `trips.txt` | Individual trip instances belonging to a route |
| `stops.txt` | Physical stop locations (name, **latitude**, **longitude**) |
| `stop_times.txt` | Arrival/departure times at each stop for every trip |

- Each **stop** becomes a **node** in the graph, storing its geographic coordinates.
- Each **consecutive stop pair** within a trip becomes a **directed edge**, weighted by the travel time (departure → arrival) in seconds.
- Edges are enriched with metadata: `trip_id`, transport `type` (BUS / METRO), and `line_name`.

### 2. Pathfinding — Dijkstra's Algorithm

When a routing request arrives with `(origin_lat, origin_lon)` → `(dest_lat, dest_lon)`:

1. **Nearest-Node Lookup**: The engine maps the GPS coordinates to the closest graph node using Euclidean distance over lat/lon.
2. **Dijkstra's SSSP**: A standard single-source shortest-path search runs from the origin node, using a min-heap priority queue. The search terminates early when the destination is reached.
3. **Path Reconstruction**: The algorithm backtracks through parent pointers to reconstruct the full sequence of nodes and edges, producing step-by-step navigation instructions.

> **Thread Safety**: The Dijkstra implementation uses local state vectors (`dist`, `parent`) instead of modifying the shared graph, allowing concurrent requests to be served safely by the gRPC server.

### 3. gRPC Service

The engine exposes a single RPC endpoint:

```protobuf
rpc GetRoute (RouteRequest) returns (RouteResponse) {}
```

- **Input**: Origin and destination as `(latitude, longitude)` pairs.
- **Output**: An ordered list of `RouteStep` objects, each containing the instruction, transport type, line name, duration, and start/end coordinates.

## 📂 Project Structure

```
RoutingEngine/
├── proto/              # gRPC contract (routing.proto)
├── include/            # Header files
│   ├── types.hpp       # Core data types (Node, Edge, Agency, Route, Trip)
│   ├── graph.hpp       # Graph class with GTFS loading
│   ├── pathfinder.hpp  # Dijkstra pathfinder
│   └── service_impl.hpp
├── src/                # Source files
│   ├── main.cpp        # Entry point — loads GTFS data, starts gRPC server
│   ├── graph.cpp       # GTFS parsing & graph construction
│   ├── pathfinder.cpp  # Dijkstra's algorithm implementation
│   └── service_impl.cpp
├── CMakeLists.txt      # Build configuration
└── Dockerfile          # Container build & runtime
```

## 🚀 Getting Started

### Prerequisites

- **Docker** (recommended), OR
- CMake ≥ 3.15, gRPC, and Protobuf installed locally.

### Running with Docker

```bash
# Build
docker build -t routing-engine .

# Run (mount your GTFS data folder)
docker run -p 50051:50051 -v /path/to/gtfs:/app/GTFS routing-engine
```

### Local Development

```bash
mkdir build && cd build
cmake ..
make -j4

export GTFS_PATH=/path/to/gtfs

./routing_server
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GTFS_PATH` | `GTFS` | Path to the folder containing GTFS `.txt` or `.csv` files |
