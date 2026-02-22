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

  const Node *GetNode(NodeID id) const;

  const std::vector<Node> &GetNodes() const;
  void loadGTFS(const std::string &folderPath);

  NodeID getNodeId(const std::string &query) const;

  std::string getTripMode(const std::string &trip_id) const;

  std::unordered_map<std::string, Agency> agencies;
  std::unordered_map<std::string, Route> routes;
  std::unordered_map<std::string, Trip> trips;
  std::unordered_map<std::string, NodeID> stop_id_map;
  std::unordered_map<std::string, NodeID> stop_name_map;
  std::unordered_map<std::string, int> route_modes;
  std::unordered_map<std::string, std::string> trip_routes;

private:
  std::vector<Node> nodes_;

  void loadRoutes(const std::string &filename);
  void loadTrips(const std::string &filename);
  void loadStops(const std::string &filename);
  void loadStopTimes(const std::string &filename);
  void generateTransferEdges();
};

#endif
