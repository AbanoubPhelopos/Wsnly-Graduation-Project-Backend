#ifndef PATHFINDER_HPP
#define PATHFINDER_HPP

#include "graph.hpp"
#include <vector>

class Pathfinder {
public:
  // Run A* for a single mode mask. Returns a RouteResult with segments.
  static RouteResult FindPath(const Graph &graph, double sLat, double sLon,
                              double dLat, double dLon, int modeMask,
                              const std::string &typeLabel);

  // Run all 4 route searches (bus, metro, microbus, optimal).
  // sLat/sLon/dLat/dLon are the raw user coordinates.
  static std::vector<RouteResult> FindAllRoutes(const Graph &graph, double sLat,
                                                double sLon, double dLat,
                                                double dLon);
};

#endif // PATHFINDER_HPP
