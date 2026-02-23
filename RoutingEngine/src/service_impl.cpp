#include "service_impl.hpp"
#include "pathfinder.hpp"
#include <cmath>
#include <iostream>

namespace {
int toIntSeconds(double value) {
  if (value <= 0.0) {
    return 0;
  }
  return static_cast<int>(std::round(value));
}

std::string formatDuration(int totalSeconds) {
  int minutes = totalSeconds / 60;
  int seconds = totalSeconds % 60;
  return std::to_string(minutes) + " min " + std::to_string(seconds) + " sec";
}

double segmentSpeed(const std::string &method) {
  if (method == "bus")
    return AVG_BUS_SPEED_MPS;
  if (method == "metro")
    return METRO_SPEED_MPS;
  if (method == "microbus")
    return MICROBUS_SPEED_MPS;
  return WALK_SPEED_MPS;
}
} // namespace

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

  // Fill new multi-option response fields.
  auto *query = reply->mutable_query();
  query->mutable_origin()->set_latitude(sLat);
  query->mutable_origin()->set_longitude(sLon);
  query->mutable_destination()->set_latitude(dLat);
  query->mutable_destination()->set_longitude(dLon);

  bool anyFound = false;

  for (const auto &r : results) {
    auto *option = reply->add_routes();
    option->set_type(r.type);

    bool found = r.totalDuration < INF;
    option->set_found(found);

    if (!found) {
      option->set_total_duration_seconds(0);
      option->set_total_duration_formatted("");
      option->set_total_segments(0);
      option->set_total_distance_meters(0.0);
      continue;
    }

    anyFound = true;

    int totalDurationSeconds = toIntSeconds(r.totalDuration);
    option->set_total_duration_seconds(totalDurationSeconds);
    option->set_total_duration_formatted(formatDuration(totalDurationSeconds));
    option->set_total_segments(static_cast<int>(r.segments.size()));

    double optionTotalDistance = 0.0;

    for (const auto &seg : r.segments) {
      double segDist = haversine(seg.startLat, seg.startLon, seg.endLat, seg.endLon);
      optionTotalDistance += segDist;

      auto *segment = option->add_segments();
      segment->mutable_start_location()->set_latitude(seg.startLat);
      segment->mutable_start_location()->set_longitude(seg.startLon);
      segment->set_start_name(seg.startName);

      segment->mutable_end_location()->set_latitude(seg.endLat);
      segment->mutable_end_location()->set_longitude(seg.endLon);
      segment->set_end_name(seg.endName);

      segment->set_method(seg.method);
      segment->set_num_stops(seg.numStops);
      segment->set_distance_meters(static_cast<int>(std::round(segDist)));

      int segDuration = toIntSeconds(segDist / segmentSpeed(seg.method));
      segment->set_duration_seconds(segDuration);
    }

    option->set_total_distance_meters(optionTotalDistance);
  }

  if (!anyFound) {
    return Status(grpc::StatusCode::NOT_FOUND,
                  "No path found between the specified locations.");
  }

  // Keep legacy best-route fields for compatibility.
  const RouteResult *best = nullptr;
  for (const auto &r : results) {
    if (r.totalDuration < INF) {
      if (!best || r.totalDuration < best->totalDuration) {
        best = &r;
      }
    }
  }

  // Map best RouteResult into legacy fields.
  reply->set_total_duration_seconds(best->totalDuration);

  double bestTotalDistance = 0.0;

  for (const auto &seg : best->segments) {
    auto *step = reply->add_steps();

    double segDist = haversine(seg.startLat, seg.startLon, seg.endLat, seg.endLon);
    bestTotalDistance += segDist;

    step->set_instruction("Take " + seg.method + " to " + seg.endName);
    step->set_distance_meters(segDist);

    step->set_duration_seconds(segDist > 0 ? segDist / segmentSpeed(seg.method) : 0);

    step->set_type(seg.method);
    step->set_line_name(""); // line name not tracked in new model

    step->mutable_start_location()->set_latitude(seg.startLat);
    step->mutable_start_location()->set_longitude(seg.startLon);
    step->mutable_end_location()->set_latitude(seg.endLat);
    step->mutable_end_location()->set_longitude(seg.endLon);
  }

  reply->set_total_distance_meters(bestTotalDistance);

  return Status::OK;
}
