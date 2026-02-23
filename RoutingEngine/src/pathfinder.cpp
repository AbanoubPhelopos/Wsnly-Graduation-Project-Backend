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

RouteResult Pathfinder::FindPath(const Graph &graph, double sLat, double sLon,
                                 double dLat, double dLon, int modeMask,
                                 const std::string &typeLabel) {
  RouteResult result;
  result.type = typeLabel;
  result.totalDuration = INF;

  const auto &nodes = graph.GetNodes();

  const std::vector<double> candidateRadii = {MAX_WALK_DISTANCE, 2500.0, 4000.0,
                                               6000.0};

  std::vector<std::pair<NodeID, double>> startNodes;
  std::vector<std::pair<NodeID, double>> endNodes;

  for (double radius : candidateRadii) {
    startNodes = graph.getNodesWithinRadius(sLat, sLon, radius, modeMask);
    endNodes = graph.getNodesWithinRadius(dLat, dLon, radius, modeMask);

    if (!startNodes.empty() && !endNodes.empty()) {
      break;
    }
  }

  double directDist = haversine(sLat, sLon, dLat, dLon);
  bool canDirectWalk = (directDist <= MAX_WALK_DISTANCE * 2);

  if (startNodes.empty() || endNodes.empty()) {
    if (canDirectWalk) {
      result.totalDuration = directDist / WALK_SPEED_MPS;
      result.segments.push_back(
          {sLon, sLat, "Origin", dLon, dLat, "Destination", "walking", 0});
    }
    return result;
  }

  // Fast end node map
  std::vector<double> end_walk_dist(nodes.size(), -1.0);
  for (const auto &en : endNodes) {
    end_walk_dist[en.first] = en.second;
  }

  auto heuristic = [&](NodeID u) {
    return haversine(nodes[u].lat, nodes[u].lon, dLat, dLon) / MAX_SPEED_MPS;
  };

  std::vector<PathInfo> info(nodes.size());
  std::priority_queue<State, std::vector<State>, std::greater<State>> pq;

  for (const auto &sn : startNodes) {
    NodeID u = sn.first;
    double walkDist = sn.second;
    double cost = walkDist / WALK_SPEED_MPS;

    info[u].g_score = cost;
    info[u].parent = -1;
    info[u].trip_id = "WALK";

    pq.push({u, cost, cost + heuristic(u), "WALK"});
  }

  double best_total = INF;
  NodeID best_end_node = -1;

  if (canDirectWalk) {
    best_total = directDist / WALK_SPEED_MPS;
    best_end_node = -2; // Denotes direct walk
  }

  while (!pq.empty()) {
    State top = pq.top();
    pq.pop();

    if (top.g_score > info[top.u].g_score)
      continue;
    if (top.g_score >= best_total)
      continue;

    // Is it an end node?
    if (end_walk_dist[top.u] >= 0.0) {
      double walk_to_dest_cost = end_walk_dist[top.u] / WALK_SPEED_MPS;
      double total_cost = top.g_score + walk_to_dest_cost;
      if (total_cost < best_total) {
        best_total = total_cost;
        best_end_node = top.u;
      }
    }

    for (const auto &edge : nodes[top.u].outgoing) {
      if (!(edge.mode & modeMask))
        continue;

      double edgeCost = edge.weight;
      if (!top.arrival_trip_id.empty() && top.arrival_trip_id != edge.trip_id &&
          edge.trip_id != "WALK" && top.arrival_trip_id != "WALK") {
        edgeCost += TRANSFER_PENALTY;
      }

      double newG = top.g_score + edgeCost;
      if (newG < info[edge.to].g_score && newG < best_total) {
        info[edge.to].g_score = newG;
        info[edge.to].parent = top.u;
        info[edge.to].trip_id = edge.trip_id;

        double newF = newG + heuristic(edge.to);
        pq.push({edge.to, newG, newF, edge.trip_id});
      }
    }
  }

  if (best_total == INF) {
    return result;
  }

  result.totalDuration = best_total;

  if (best_end_node == -2) {
    result.segments.push_back(
        {sLon, sLat, "Origin", dLon, dLat, "Destination", "walking", 0});
    return result;
  }

  // Reconstruct Path into Segments
  std::vector<NodeID> path;
  NodeID curr = best_end_node;
  while (curr != -1) {
    path.push_back(curr);
    curr = info[curr].parent;
  }
  std::reverse(path.begin(), path.end());

  result.segments.push_back({sLon, sLat, "Origin", nodes[path[0]].lon,
                             nodes[path[0]].lat, nodes[path[0]].stop_name,
                             "walking", 0});

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

  result.segments.push_back({nodes[best_end_node].lon, nodes[best_end_node].lat,
                             nodes[best_end_node].stop_name, dLon, dLat,
                             "Destination", "walking", 0});

  return result;
}

std::vector<RouteResult> Pathfinder::FindAllRoutes(const Graph &graph,
                                                   double sLat, double sLon,
                                                   double dLat, double dLon) {

  std::vector<RouteResult> results;

  auto startNodes = graph.getNodesWithinRadius(sLat, sLon, MAX_WALK_DISTANCE);
  auto endNodes = graph.getNodesWithinRadius(dLat, dLon, MAX_WALK_DISTANCE);

  std::cout << "[Info] Found " << startNodes.size() << " stops near origin, "
            << endNodes.size() << " stops near destination." << std::endl;

  // Run all 4 route searches
  results.push_back(
      FindPath(graph, sLat, sLon, dLat, dLon, BUS | WALK, "bus_only"));
  results.push_back(
      FindPath(graph, sLat, sLon, dLat, dLon, METRO | WALK, "metro_only"));
  results.push_back(FindPath(graph, sLat, sLon, dLat, dLon, MICROBUS | WALK,
                             "microbus_only"));
  results.push_back(
      FindPath(graph, sLat, sLon, dLat, dLon, ANY | WALK, "optimal"));

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
