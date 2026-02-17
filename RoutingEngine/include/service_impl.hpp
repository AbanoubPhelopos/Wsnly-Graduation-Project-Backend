#ifndef SERVICE_IMPL_HPP
#define SERVICE_IMPL_HPP

#include "graph.hpp"
#include "routing.grpc.pb.h"
#include <grpcpp/grpcpp.h>


using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;
using routing::RouteRequest;
using routing::RouteResponse;
using routing::RoutingService;

class RoutingServiceImpl final : public RoutingService::Service {
public:
  explicit RoutingServiceImpl(const Graph &graph) : graph_(graph) {}
  Status GetRoute(ServerContext *context, const RouteRequest *request,
                  RouteResponse *reply) override;

private:
  const Graph &graph_;
};

#endif // SERVICE_IMPL_HPP
