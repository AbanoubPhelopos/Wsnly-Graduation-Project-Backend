# Shared Protobuf Contracts

This directory is the canonical source for gRPC contract files used by all services.

- `interpreter.proto` defines the AI extraction service contract.
- `routing.proto` defines the routing engine service contract.

Service-local proto copies must stay byte-compatible with these files until all services are migrated to compile directly from `shared/protos`.
