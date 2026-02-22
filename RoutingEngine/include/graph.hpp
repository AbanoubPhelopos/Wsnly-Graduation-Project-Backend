#ifndef GRAPH_HPP
#define GRAPH_HPP

#include "types.hpp"
#include <string>
#include <unordered_map>
#include <vector>

std::string stripOuterQuotes(const std::string &s);
std::vector<std::string> parseCSVLine(const std::string &rawLine);

class Graph {
public:
  NodeID findNearestNode(double lat, double lon) const;
  NodeID findNearestNode(double lat, double lon, int modeMask) const;

  // Faster lookup returning all nodes within a search radius (meters) using
  // spatial grid
  std::vector<std::pair<NodeID, double>>
  getNodesWithinRadius(double lat, double lon, double radius) const;
  std::vector<std::pair<NodeID, double>>
  getNodesWithinRadius(double lat, double lon, double radius,
                       int modeMask) const;

  const Node *GetNode(NodeID id) const;

  const std::vector<Node> &GetNodes() const;
  void loadGTFS(const std::string &folderPath);

  NodeID getNodeId(const std::string &query) const;

  std::string getTripMode(const std::string &trip_id) const;

  // --- GTFS Data Maps ---
  std::unordered_map<std::string, Agency> agencies;
  std::unordered_map<std::string, Route> routes;
  std::unordered_map<std::string, Trip> trips;
  std::unordered_map<std::string, NodeID> stop_id_map;
  std::unordered_map<std::string, NodeID> stop_name_map;
  std::unordered_map<std::string, int> route_modes;
  std::unordered_map<std::string, std::string> trip_routes;

private:
  std::vector<Node> nodes_;

  // Spatial Grid Cache for O(1) lookups
  // Based on MAX_WALK_DISTANCE: 1 degree approx 111km
  const double CELL_SIZE = MAX_WALK_DISTANCE / 111000.0;
  std::unordered_map<long long, std::vector<NodeID>> spatial_grid_;
  long long getCellKey(double lat, double lon) const {
    int cx = (int)std::floor(lon / CELL_SIZE);
    int cy = (int)std::floor(lat / CELL_SIZE);
    return (long long)cy * 1000000LL + cx;
  }

  void loadRoutes(const std::string &filename);
  void loadTrips(const std::string &filename);
  void loadStops(const std::string &filename);
  void loadStopTimes(const std::string &filename);
  void generateTransferEdges();
};

#endif
