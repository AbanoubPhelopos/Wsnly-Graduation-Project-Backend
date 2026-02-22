#include "service_impl.hpp"
#include "pathfinder.hpp"
#include <iostream>

Status RoutingServiceImpl::GetRoute(ServerContext *context,
                                    const RouteRequest *request,
                                    RouteResponse *reply) {
  double sLat = request->origin().latitude();
  double sLon = request->origin().longitude();
  double dLat = request->destination().latitude();
  double dLon = request->destination().longitude();

  std::cout << "Received request: From (" << sLat << ", " << sLon << ") to ("
            << dLat << ", " << dLon << ")" << std::endl;

  // Run all route searches
  auto results = Pathfinder::FindAllRoutes(graph_, sLat, sLon, dLat, dLon);

  // Find the best result (lowest duration)
  const RouteResult *best = nullptr;
  for (const auto &r : results) {
    if (r.totalDuration < INF) {
      if (!best || r.totalDuration < best->totalDuration) {
        best = &r;
      }
    }
  }

  if (!best) {
    return Status(grpc::StatusCode::NOT_FOUND,
                  "No path found between the specified locations.");
  }

  // Map best RouteResult into proto response
  reply->set_total_duration_seconds(best->totalDuration);
  reply->set_total_distance_meters(0); // TODO: compute total distance

  for (const auto &seg : best->segments) {
    auto *step = reply->add_steps();

    double segDist =
        haversine(seg.startLat, seg.startLon, seg.endLat, seg.endLon);

    step->set_instruction("Take " + seg.method + " to " + seg.endName);
    step->set_distance_meters(segDist);

    // Estimate duration from distance & mode speed
    double speed = WALK_SPEED_MPS;
    if (seg.method == "bus")
      speed = AVG_BUS_SPEED_MPS;
    if (seg.method == "metro")
      speed = METRO_SPEED_MPS;
    if (seg.method == "microbus")
      speed = MICROBUS_SPEED_MPS;
    step->set_duration_seconds(segDist > 0 ? segDist / speed : 0);

    step->set_type(seg.method);
    step->set_line_name(""); // line name not tracked in new model

    step->mutable_start_location()->set_latitude(seg.startLat);
    step->mutable_start_location()->set_longitude(seg.startLon);
    step->mutable_end_location()->set_latitude(seg.endLat);
    step->mutable_end_location()->set_longitude(seg.endLon);
  }

  return Status::OK;
}
