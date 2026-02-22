#include "pathfinder.hpp"
#include <algorithm>
#include <iostream>
#include <queue>
#include <vector>

// --- A* Search State ---
struct State {
  NodeID u;
  Weight g_score;
  Weight f_score;
  std::string arrival_trip_id;

  bool operator>(const State &other) const { return f_score > other.f_score; }
};

struct PathInfo {
  Weight g_score = INF;
  NodeID parent = -1;
  std::string trip_id = "";
};

RouteResult Pathfinder::FindPath(const Graph &graph, NodeID startNode,
                                 NodeID endNode, int modeMask, double walkStart,
                                 double walkEnd, double sLat, double sLon,
                                 double dLat, double dLon,
                                 const std::string &typeLabel) {
  RouteResult result;
  result.type = typeLabel;
  result.totalDuration = 0;

  const auto &nodes = graph.GetNodes();

  if (startNode < 0 || startNode >= (int)nodes.size() || endNode < 0 ||
      endNode >= (int)nodes.size()) {
    result.totalDuration = INF;
    return result;
  }

  // A* heuristic: optimistic travel time to destination
  auto heuristic = [&](NodeID u) {
    double dist = haversine(nodes[u].lat, nodes[u].lon, dLat, dLon);
    return dist / MAX_SPEED_MPS;
  };

  std::vector<PathInfo> info(nodes.size());
  std::priority_queue<State, std::vector<State>, std::greater<State>> pq;

  info[startNode].g_score = 0;
  pq.push({startNode, 0, 0 + heuristic(startNode), ""});

  while (!pq.empty()) {
    State top = pq.top();
    pq.pop();

    if (top.g_score > info[top.u].g_score)
      continue;
    if (top.u == endNode)
      break;

    for (const auto &edge : nodes[top.u].outgoing) {
      // Mode filtering: only traverse edges matching the mode mask
      if (!(edge.mode & modeMask))
        continue;

      double edgeCost = edge.weight;

      // Transfer Penalty: switching between different vehicle trips
      if (!top.arrival_trip_id.empty() && top.arrival_trip_id != edge.trip_id &&
          edge.trip_id != "WALK" && top.arrival_trip_id != "WALK") {
        edgeCost += TRANSFER_PENALTY;
      }

      double newG = top.g_score + edgeCost;

      if (newG < info[edge.to].g_score) {
        info[edge.to].g_score = newG;
        info[edge.to].parent = top.u;
        info[edge.to].trip_id = edge.trip_id;

        double newF = newG + heuristic(edge.to);
        pq.push({edge.to, newG, newF, edge.trip_id});
      }
    }
  }

  if (info[endNode].g_score == INF) {
    result.totalDuration = INF;
    return result;
  }

  result.totalDuration = info[endNode].g_score + (walkStart / WALK_SPEED_MPS) +
                         (walkEnd / WALK_SPEED_MPS);

  // --- Reconstruct Path into Segments ---
  std::vector<NodeID> path;
  NodeID curr = endNode;
  while (curr != -1) {
    path.push_back(curr);
    curr = info[curr].parent;
  }
  std::reverse(path.begin(), path.end());

  // 1. Initial Walking Segment (from user origin to first stop)
  result.segments.push_back({sLon, sLat, "Origin", nodes[path[0]].lon,
                             nodes[path[0]].lat, nodes[path[0]].stop_name,
                             "walking", 0});

  // 2. Transit Segments (grouped by trip)
  if (path.size() > 1) {
    size_t startIdx = 0;

    for (size_t i = 1; i < path.size(); ++i) {
      std::string currentTrip = info[path[i]].trip_id;
      bool isLast = (i == path.size() - 1);
      bool nextTripDifferent = false;

      if (!isLast) {
        if (info[path[i + 1]].trip_id != currentTrip)
          nextTripDifferent = true;
      }

      if (isLast || nextTripDifferent) {
        NodeID u = path[startIdx];
        NodeID v = path[i];
        std::string mode = graph.getTripMode(currentTrip);
        int count = (int)(i - startIdx);

        result.segments.push_back(
            {nodes[u].lon, nodes[u].lat, nodes[u].stop_name, nodes[v].lon,
             nodes[v].lat, nodes[v].stop_name, mode, count});
        startIdx = i;
      }
    }
  }

  // 3. Final Walking Segment (from last stop to user destination)
  result.segments.push_back({nodes[endNode].lon, nodes[endNode].lat,
                             nodes[endNode].stop_name, dLon, dLat,
                             "Destination", "walking", 0});

  return result;
}

std::vector<RouteResult> Pathfinder::FindAllRoutes(const Graph &graph,
                                                   double sLat, double sLon,
                                                   double dLat, double dLon) {
  // Find nearest graph nodes to user coordinates
  NodeID start = graph.findNearestNode(sLat, sLon);
  NodeID end = graph.findNearestNode(dLat, dLon);

  std::vector<RouteResult> results;

  if (start == -1 || end == -1) {
    // Return 4 empty results
    for (const auto &label :
         {"bus_only", "metro_only", "microbus_only", "optimal"}) {
      RouteResult r;
      r.type = label;
      r.totalDuration = INF;
      results.push_back(r);
    }
    return results;
  }

  const auto &nodes = graph.GetNodes();
  double walkStart = haversine(sLat, sLon, nodes[start].lat, nodes[start].lon);
  double walkEnd = haversine(dLat, dLon, nodes[end].lat, nodes[end].lon);

  std::cout << "[Info] Nearest start stop: " << nodes[start].stop_name << " ("
            << walkStart << "m away)" << std::endl;
  std::cout << "[Info] Nearest end stop:   " << nodes[end].stop_name << " ("
            << walkEnd << "m away)" << std::endl;

  // Run all 4 route searches — WALK is always included so walking
  // transfer edges can be used even in single-mode searches
  results.push_back(FindPath(graph, start, end, BUS | WALK, walkStart, walkEnd,
                             sLat, sLon, dLat, dLon, "bus_only"));
  results.push_back(FindPath(graph, start, end, METRO | WALK, walkStart,
                             walkEnd, sLat, sLon, dLat, dLon, "metro_only"));
  results.push_back(FindPath(graph, start, end, MICROBUS | WALK, walkStart,
                             walkEnd, sLat, sLon, dLat, dLon, "microbus_only"));
  results.push_back(FindPath(graph, start, end, ANY | WALK, walkStart, walkEnd,
                             sLat, sLon, dLat, dLon, "optimal"));

  // Print summary
  std::cout << "\n=== Route Results ===" << std::endl;
  for (const auto &r : results) {
    if (r.totalDuration < INF) {
      std::cout << r.type << ": " << (int)(r.totalDuration / 60) << " min, "
                << r.segments.size() << " segments" << std::endl;
    } else {
      std::cout << r.type << ": No path found" << std::endl;
    }
  }

  return results;
}
