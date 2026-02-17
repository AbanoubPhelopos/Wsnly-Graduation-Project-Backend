#ifndef TYPES_HPP
#define TYPES_HPP

#include <limits>
#include <string>
#include <vector>

using NodeID = int;
using Weight = double;
const double INF = std::numeric_limits<double>::max();

struct Agency {
  std::string id;
  std::string name;
};

struct Route {
  std::string id;
  std::string agency_id;
  std::string short_name;
  int type;
};

struct Trip {
  std::string id;
  std::string route_id;
  std::string service_id;
};

struct Edge {
  NodeID to;
  Weight weight;
  std::string trip_id;   // Link to Trip
  std::string type;      // "METRO", "BUS", "WALK" - inferred from route type
  std::string line_name; // e.g., "Line 1" - inferred from route short_name
};

struct Node {
  NodeID id;
  std::string name; // stop_name
  std::string gtfs_stop_id;
  double lat;
  double lon;
  std::vector<Edge> outgoing;
};

#endif
