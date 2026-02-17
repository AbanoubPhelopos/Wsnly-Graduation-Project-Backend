#ifndef PATHFINDER_HPP
#define PATHFINDER_HPP

#include "graph.hpp"
#include <vector>

// Struct to hold the result of a path search
struct PathResult {
  std::vector<NodeID> path_nodes;
  std::vector<Edge> path_edges; // To keep track of which edge was taken (needed
                                // for instructions)
  double total_distance;
  double total_duration;
  bool found;
};

class Pathfinder {
public:
  static PathResult FindPath(const Graph &graph, NodeID startInfo,
                             NodeID endInfo);
};

#endif // PATHFINDER_HPP
