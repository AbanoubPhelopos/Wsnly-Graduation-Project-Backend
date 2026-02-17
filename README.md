# 🚌 Wslny

**Wslny** is a comprehensive transportation platform designed to streamline commutes and logistics through a modern digital ecosystem for Greater Cairo's public transportation.

The project is divided into two main components: a powerful backend API and a high-performance routing engine, supported by a web admin panel and a mobile application.

## 📂 Repository Structure

```
Graduation-Project/
├── API/             # Django backend — business logic, auth, data management
├── RoutingEngine/   # C++ microservice — graph-based transit pathfinding
└── README.md
```

---

### 1. `API` — Backend Service

The backend service responsible for business logic, data management, and authentication.

| | |
|---|---|
| **Technology** | Python, Django, Django REST Framework |
| **Architecture** | Clean Architecture with CQRS |

**Key Features:**
- Secure JWT-based authentication with Google Login support
- Role management (Users, Admins)
- Fully Dockerized deployment

📖 See [`API/README.md`](API/README.md) for setup and API details.

---

### 2. `RoutingEngine` — Pathfinding Microservice

A high-performance C++ microservice that finds optimal routes across Cairo's multi-modal transit network.

| | |
|---|---|
| **Technology** | C++17, CMake, gRPC, Protocol Buffers |
| **Data Source** | GTFS (General Transit Feed Specification) |
| **Algorithm** | Dijkstra's Shortest Path |

**How It Works:**
1. On startup, parses GTFS data (`stops`, `routes`, `trips`, `stop_times`) into a weighted directed graph.
2. Receives routing requests via gRPC with origin/destination coordinates.
3. Maps coordinates to the nearest transit stops using spatial lookup.
4. Runs Dijkstra's algorithm to find the fastest path, returning step-by-step navigation with transport type, line name, and durations.

📖 See [`RoutingEngine/README.md`](RoutingEngine/README.md) for architecture and algorithm details.

---

## 🏗️ Architecture Overview

```
┌──────────────┐        gRPC         ┌──────────────────┐
│   Django API │ ◄──────────────────► │  Routing Engine  │
│  (Python)    │   (Proto Buffers)    │     (C++17)      │
└──────┬───────┘                     └────────┬─────────┘
       │                                      │
       ▼                                      ▼
   Database                             GTFS Data Files
  (PostgreSQL)                     (stops, routes, trips...)
```

## 🚀 Getting Started

Each component has its own setup instructions. Refer to:

- **Backend**: [`API/README.md`](API/README.md)
- **Routing Engine**: [`RoutingEngine/README.md`](RoutingEngine/README.md)

Both services are containerized and can be run together with Docker Compose.