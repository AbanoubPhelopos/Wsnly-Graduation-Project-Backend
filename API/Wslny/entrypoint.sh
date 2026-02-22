#!/bin/bash
set -e

# Generate gRPC Python stubs for internal clients
echo "Generating gRPC stubs..."
mkdir -p /app/src/Infrastructure/GrpcClients/stubs
touch /app/src/Infrastructure/GrpcClients/stubs/__init__.py
python -m grpc_tools.protoc \
  -I./protos \
  --python_out=./src/Infrastructure/GrpcClients/stubs \
  --grpc_python_out=./src/Infrastructure/GrpcClients/stubs \
  ./protos/interpreter.proto \
  ./protos/routing.proto

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Seed database
echo "Seeding database..."
python manage.py seed_admin

# Start server
echo "Starting server..."
exec "$@"
