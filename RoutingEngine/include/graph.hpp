#ifndef GRAPH_HPP
#define GRAPH_HPP

#include "types.hpp"
#include <string>
#include <unordered_map>
#include <vector>

class Graph {
public:
  // Add a node to the graph
  void AddNode(NodeID id, const std::string &name, double lat, double lon);

  // Add a directed edge
  void AddEdge(NodeID from, NodeID to, Weight weight, const std::string &type,
               const std::string &line_name = "");

  // Find the nearest node to a given lat/lon (Linear search for now, TODO:
  // Spatial Index)
  NodeID FindNearestNode(double lat, double lon) const;

  // Get a node by ID
  const Node *GetNode(NodeID id) const;

  // Get all nodes (const reference)
  const std::vector<Node> &GetNodes() const;

  // Load GTFS data from a folder
  void loadGTFS(const std::string &folderPath);

  // Get a node ID by GTFS stop_id or name
  NodeID getNodeId(const std::string &query) const;

  // Data Maps
  std::unordered_map<std::string, Agency> agencies;
  std::unordered_map<std::string, Route> routes;
  std::unordered_map<std::string, Trip> trips;
  std::unordered_map<std::string, NodeID> stop_id_map;
  std::unordered_map<std::string, NodeID> stop_name_map;

private:
  std::vector<Node> nodes_; // stores all nodes

  // Helper loaders
  void loadAgencies(const std::string &filename);
  void loadRoutes(const std::string &filename);
  void loadTrips(const std::string &filename);
  void loadStops(const std::string &filename);
  void loadStopTimes(const std::string &filename);

  // Helpers
  std::string clean(std::string s);
  double parseTime(const std::string &timeStr);
};

#endif // GRAPH_HPP
