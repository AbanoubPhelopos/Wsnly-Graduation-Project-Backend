#ifndef TYPES_HPP
#define TYPES_HPP

#include <cmath>
#include <limits>
#include <string>
#include <vector>

// --- Core Type Aliases ---
using NodeID = int;
using Weight = double;

// --- Constants ---
const double INF = std::numeric_limits<double>::max();
const double R_EARTH = 6371000.0;
const double PI = 3.14159265358979323846;

// Physics Fallbacks (m/s)
const double AVG_BUS_SPEED_MPS = 8.33;   // ~30 km/h
const double WALK_SPEED_MPS = 1.4;       // ~5 km/h
const double METRO_SPEED_MPS = 16.67;    // ~60 km/h
const double MICROBUS_SPEED_MPS = 11.11; // ~40 km/h

// Optimization Parameters
const double TRANSFER_PENALTY = 60.0;    // 1 min penalty to switch vehicles
const double STOP_DWELL_TIME = 30.0;     // 30s wait at each stop
const double MAX_SPEED_MPS = 25.0;       // For A* heuristic
const double MAX_WALK_DISTANCE = 1500.0; // Max walking transfer distance (m)

// --- Transport Modes (bitmask) ---
enum Mode {
  NONE = 0,
  METRO = 1 << 0,
  BUS = 1 << 1,
  MICROBUS = 1 << 2,
  WALK = 1 << 3,
  ANY = METRO | BUS | MICROBUS
};

inline std::string modeToString(int mode) {
  if (mode == METRO)
    return "metro";
  if (mode == BUS)
    return "bus";
  if (mode == MICROBUS)
    return "microbus";
  if (mode == WALK)
    return "walking";
  if (mode == ANY)
    return "optimal";
  return "unknown";
}

// --- Haversine Distance (meters) ---
inline double toRadians(double degree) { return degree * PI / 180.0; }

inline double haversine(double lat1, double lon1, double lat2, double lon2) {
  double dLat = toRadians(lat2 - lat1);
  double dLon = toRadians(lon2 - lon1);
  lat1 = toRadians(lat1);
  lat2 = toRadians(lat2);
  double a =
      std::sin(dLat / 2) * std::sin(dLat / 2) +
      std::sin(dLon / 2) * std::sin(dLon / 2) * std::cos(lat1) * std::cos(lat2);
  double c = 2 * std::atan2(std::sqrt(a), std::sqrt(1 - a));
  return R_EARTH * c;
}

// --- Graph Structures ---
struct Edge {
  NodeID to;
  Weight weight;       // Travel time in seconds
  std::string trip_id; // GTFS trip ID (or "WALK" for walking edges)
  int mode;            // Transport mode bitmask
};

struct Node {
  NodeID id;
  std::string stop_name;
  std::string gtfs_stop_id;
  double lat;
  double lon;
  std::vector<Edge> outgoing;
};

// --- GTFS Reference Structs ---
struct Agency {
  std::string id;
  std::string name;
};

struct Route {
  std::string id;
  std::string agency_id;
  std::string short_name;
  int type; // GTFS route_type
};

struct Trip {
  std::string id;
  std::string route_id;
  std::string service_id;
};

// --- Output Structures ---
struct RouteSegment {
  double startLon;
  double startLat;
  std::string startName;
  double endLon;
  double endLat;
  std::string endName;
  std::string method; // "bus", "metro", "microbus", "walking"
  int numStops;
};

struct RouteResult {
  std::string type;     // "bus_only", "metro_only", "microbus_only", "optimal"
  double totalDuration; // seconds
  std::vector<RouteSegment> segments;

  double getScore() const { return totalDuration; }
  bool operator<(const RouteResult &other) const {
    return getScore() < other.getScore();
  }
};

#endif // TYPES_HPP
