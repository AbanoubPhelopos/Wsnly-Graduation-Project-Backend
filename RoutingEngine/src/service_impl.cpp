#include "service_impl.hpp"
#include "pathfinder.hpp"
#include <iostream>

Status RoutingServiceImpl::GetRoute(ServerContext *context,
                                    const RouteRequest *request,
                                    RouteResponse *reply) {
  std::cout << "Received request: From (" << request->origin().latitude()
            << ", " << request->origin().longitude() << ") to ("
            << request->destination().latitude() << ", "
            << request->destination().longitude() << ")" << std::endl;

  NodeID startNode = graph_.FindNearestNode(request->origin().latitude(),
                                            request->origin().longitude());
  NodeID endNode = graph_.FindNearestNode(request->destination().latitude(),
                                          request->destination().longitude());

  if (startNode == -1 || endNode == -1) {
    return Status(grpc::StatusCode::NOT_FOUND,
                  "Could not map coordinates to graph nodes.");
  }

  std::cout << "Mapped to Nodes: " << startNode << " -> " << endNode
            << std::endl;

  PathResult result = Pathfinder::FindPath(graph_, startNode, endNode);

  if (!result.found) {
    return Status(grpc::StatusCode::NOT_FOUND,
                  "No path found between the specified locations.");
  }

  reply->set_total_distance_meters(result.total_distance);
  reply->set_total_duration_seconds(result.total_duration);

  for (size_t i = 0; i < result.path_nodes.size(); ++i) {
    if (i < result.path_edges.size()) {
      auto *step = reply->add_steps();
      const Edge &edge = result.path_edges[i];
      const Node *u = graph_.GetNode(result.path_nodes[i]);
      const Node *v = graph_.GetNode(result.path_nodes[i + 1]);

      std::string destName = v ? v->name : "next stop";
      step->set_instruction("Take " + edge.type + " " + edge.line_name +
                            " to " + destName);
      step->set_distance_meters(0);
      step->set_duration_seconds(edge.weight);
      step->set_type(edge.type);
      step->set_line_name(edge.line_name);

      if (u) {
        step->mutable_start_location()->set_latitude(u->lat);
        step->mutable_start_location()->set_longitude(u->lon);
      }
      if (v) {
        step->mutable_end_location()->set_latitude(v->lat);
        step->mutable_end_location()->set_longitude(v->lon);
      }
    }
  }

  return Status::OK;
}
