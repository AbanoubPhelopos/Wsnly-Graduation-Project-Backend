# Shared Protobuf Contracts

This directory is the canonical source for gRPC contract files used by all services.

- `interpreter.proto` defines the AI extraction service contract.
  - `to_coordinates` is required for a usable extraction result.
  - `from_coordinates` may be omitted for destination-only text; API can use client current location.
- `routing.proto` defines the routing engine service contract.
  - Legacy single-route fields are kept for compatibility.
  - New `query` and `routes[]` fields provide multi-option outputs (`bus_only`, `metro_only`, `microbus_only`, `optimal`).

Service-local proto copies must stay byte-compatible with these files until all services are migrated to compile directly from `shared/protos`.
