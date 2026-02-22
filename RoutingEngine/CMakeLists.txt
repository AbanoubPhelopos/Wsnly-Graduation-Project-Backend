cmake_minimum_required(VERSION 3.15)
project(RoutingEngine CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Protobuf and gRPC
find_package(Protobuf REQUIRED)
find_package(gRPC CONFIG REQUIRED)

# Proto functionality
set(PROTO_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(PROTO_BINARY_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY ${PROTO_BINARY_DIR})

# Generate Sources from Proto
set(PROTO_FILES "${PROTO_SRC_DIR}/routing.proto")

# Include directories
include_directories(
  "${CMAKE_CURRENT_SOURCE_DIR}/include"
  "${PROTO_BINARY_DIR}"
)

# Find the gRPC C++ plugin
find_program(GRPC_CPP_PLUGIN grpc_cpp_plugin)

# Compile Proto
add_custom_command(
  OUTPUT "${PROTO_BINARY_DIR}/routing.pb.cc" "${PROTO_BINARY_DIR}/routing.pb.h" "${PROTO_BINARY_DIR}/routing.grpc.pb.cc" "${PROTO_BINARY_DIR}/routing.grpc.pb.h"
  COMMAND protoc
    -I "${PROTO_SRC_DIR}"
    --cpp_out="${PROTO_BINARY_DIR}"
    --grpc_out="${PROTO_BINARY_DIR}"
    --plugin=protoc-gen-grpc=${GRPC_CPP_PLUGIN}
    "${PROTO_FILES}"
  DEPENDS "${PROTO_FILES}"
)

# Add Executable
add_executable(routing_server
  src/main.cpp
  src/graph.cpp
  src/pathfinder.cpp
  src/service_impl.cpp
  "${PROTO_BINARY_DIR}/routing.pb.cc"
  "${PROTO_BINARY_DIR}/routing.grpc.pb.cc"
)

# Link Libraries
target_link_libraries(routing_server
  PRIVATE
    gRPC::grpc++
    protobuf::libprotobuf
)
