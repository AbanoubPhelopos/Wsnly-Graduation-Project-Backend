# Use an official lightweight C++ image.
# Debian Bookworm has recent enough packages for gRPC and CMake.
FROM debian:bookworm-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libgrpc++-dev \
    libprotobuf-dev \
    protobuf-compiler-grpc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN mkdir -p build && cd build && \
    cmake .. && \
    make -j1

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    libgrpc++1.51 \
    libprotobuf32 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/build/routing_server /app/routing_server
COPY --from=builder /app/Database /app/Database

ENV GTFS_PATH=/app/Database

EXPOSE 50051

CMD ["./routing_server"]
