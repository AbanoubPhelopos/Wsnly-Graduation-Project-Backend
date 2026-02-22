#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <queue>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

// --- Constants ---
const double INF = std::numeric_limits<double>::max();
const double R_EARTH = 6371000.0;
const double PI = 3.14159265358979323846;

// Physics Fallbacks
const double AVG_BUS_SPEED_MPS = 8.33;   // ~30 km/h (Bus Speed)
const double WALK_SPEED_MPS = 1.4;       // ~5 km/h (Walking)
const double METRO_SPEED_MPS = 16.67;    // ~60 km/h (Metro Speed)
const double MICROBUS_SPEED_MPS = 11.11; // ~40 km/h (Microbus Speed)

// Optimization Parameters
const double TRANSFER_PENALTY = 60.0; // 1 min penalty to switch vehicles
const double STOP_DWELL_TIME = 30.0;  // 30s wait at stop
const double MAX_SPEED_MPS = 25.0;    // For A* Heuristic
const double MAX_WALK_DISTANCE =
    1500.0; // Max walking transfer distance in meters

using NodeID = int;
using Weight = double;

// --- Transport Modes ---
enum Mode {
  NONE = 0,
  METRO = 1 << 0,
  BUS = 1 << 1,
  MICROBUS = 1 << 2,
  WALK = 1 << 3,
  ANY = METRO | BUS | MICROBUS
};

std::string modeToString(int mode) {
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

// --- Helper Functions ---
double toRadians(double degree) { return degree * PI / 180.0; }

double haversine(double lat1, double lon1, double lat2, double lon2) {
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

// --- CSV Parsing ---
// The GTFS CSV files wrap each entire row in outer quotes: "col1,col2,col3"
// We strip those outer quotes, then split by comma, handling inner quoted
// fields.
std::string stripOuterQuotes(const std::string &s) {
  std::string result = s;
  // Trim whitespace/CR/LF
  while (!result.empty() && (result.back() == '\r' || result.back() == '\n' ||
                             result.back() == ' ' || result.back() == '\t'))
    result.pop_back();
  while (!result.empty() && (result.front() == ' ' || result.front() == '\t'))
    result.erase(result.begin());

  // Strip one layer of outer quotes if the entire line is wrapped
  if (result.size() >= 2 && result.front() == '"' && result.back() == '"') {
    result = result.substr(1, result.size() - 2);
  }
  return result;
}

std::vector<std::string> parseCSVLine(const std::string &rawLine) {
  std::string line = stripOuterQuotes(rawLine);
  std::vector<std::string> cols;
  std::string field;
  bool inQuotes = false;

  for (size_t i = 0; i < line.size(); ++i) {
    char c = line[i];
    if (c == '"') {
      if (inQuotes && i + 1 < line.size() && line[i + 1] == '"') {
        field += '"'; // escaped quote
        ++i;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (c == ',' && !inQuotes) {
      cols.push_back(field);
      field.clear();
    } else {
      field += c;
    }
  }
  cols.push_back(field);
  return cols;
}

// --- Graph Structures ---
struct Edge {
  NodeID to;
  Weight weight;       // Physical travel time
  std::string trip_id; // To track transfers
  int mode;            // Transport mode
};

struct Node {
  NodeID id;
  std::string gtfs_stop_id;
  std::string stop_name;
  double lat;
  double lon;
  std::vector<Edge> outgoing;
};

// --- Output Structures ---
struct RouteSegment {
  double startLon;
  double startLat;
  std::string startName;
  double endLon;
  double endLat;
  std::string endName;
  std::string method;
  int numStops;
};

struct RouteResult {
  std::string type;
  double totalDuration;
  std::vector<RouteSegment> segments;

  double getScore() const { return totalDuration; }

  bool operator<(const RouteResult &other) const {
    return getScore() < other.getScore();
  }
};

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

class GTFSGraph {
public:
  std::vector<Node> nodes;
  std::unordered_map<std::string, NodeID> stop_id_map;
  std::unordered_map<std::string, int> route_modes;         // RouteID -> Mode
  std::unordered_map<std::string, std::string> trip_routes; // TripID -> RouteID

  void loadGTFS(const std::string &folderPath) {
    std::cout << "[Graph] Loading GTFS Data..." << std::endl;
    loadRoutes(folderPath + "/routes.csv");
    loadTrips(folderPath + "/trips.csv");
    loadStops(folderPath + "/stops.csv");
    loadStopTimes(folderPath + "/stop_times.csv");
    generateTransferEdges();
    std::cout << "[Graph] Loaded " << nodes.size() << " stops." << std::endl;
  }

  NodeID findNearestNode(double lat, double lon) {
    NodeID bestNode = -1;
    double minDist = INF;
    for (const auto &node : nodes) {
      double dist = haversine(lat, lon, node.lat, node.lon);
      if (dist < minDist) {
        minDist = dist;
        bestNode = node.id;
      }
    }
    return bestNode;
  }

  // Mode-specific: prefer stops that match the search mode
  NodeID findNearestNode(double lat, double lon, int modeMask) {
    // Determine prefix filter based on mode
    std::vector<std::string> prefixes;
    if (modeMask & METRO)
      prefixes.push_back("M_");
    if (modeMask & BUS)
      prefixes.push_back("B1_");
    if (modeMask & MICROBUS)
      prefixes.push_back("MB_");

    auto matchesMode = [&](const std::string &stop_id) {
      for (const auto &p : prefixes)
        if (stop_id.substr(0, p.size()) == p)
          return true;
      return false;
    };

    NodeID bestNode = -1;
    double minDist = INF;
    for (const auto &node : nodes) {
      if (!matchesMode(node.gtfs_stop_id))
        continue;
      double dist = haversine(lat, lon, node.lat, node.lon);
      if (dist < minDist) {
        minDist = dist;
        bestNode = node.id;
      }
    }

    // Fallback: if nothing within 5km, use any node
    if (bestNode == -1 || minDist > 5000.0)
      return findNearestNode(lat, lon);
    return bestNode;
  }

  std::string getTripMode(const std::string &trip_id) {
    if (trip_id == "WALK")
      return "walking";
    if (trip_routes.count(trip_id)) {
      std::string route_id = trip_routes[trip_id];
      if (route_modes.count(route_id)) {
        return modeToString(route_modes[route_id]);
      }
    }
    return "unknown";
  }

private:
  void loadRoutes(const std::string &filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
      std::cerr << "[Error] Cannot open " << filename << std::endl;
      return;
    }
    std::string line;
    std::getline(file, line); // Header
    while (std::getline(file, line)) {
      auto cols = parseCSVLine(line);
      if (cols.size() >= 2) {
        std::string route_id = cols[0];
        std::string agency_id = cols[1];
        int mode = BUS;
        if (agency_id == "M_CAI-METRO")
          mode = METRO;
        else if (agency_id == "MB_CAI_BUS")
          mode = MICROBUS;
        else if (agency_id == "B1_CAI_BUS")
          mode = BUS;

        route_modes[route_id] = mode;
      }
    }
    std::cout << "[Graph] Loaded " << route_modes.size() << " routes."
              << std::endl;
  }

  void loadTrips(const std::string &filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
      std::cerr << "[Error] Cannot open " << filename << std::endl;
      return;
    }
    std::string line;
    std::getline(file, line); // Header
    while (std::getline(file, line)) {
      auto cols = parseCSVLine(line);
      if (cols.size() >= 3) {
        std::string route_id = cols[0];
        std::string trip_id = cols[2];
        trip_routes[trip_id] = route_id;
      }
    }
    std::cout << "[Graph] Loaded " << trip_routes.size() << " trips."
              << std::endl;
  }

  void loadStops(const std::string &filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
      std::cerr << "[Error] Cannot open " << filename << std::endl;
      return;
    }
    std::string line;
    std::getline(file, line); // Header
    while (std::getline(file, line)) {
      auto cols = parseCSVLine(line);
      if (cols.size() >= 4) {
        std::string stop_id = cols[0];
        std::string stop_name = cols[1];
        double lat = 0.0, lon = 0.0;
        try {
          lat = std::stod(cols[2]);
          lon = std::stod(cols[3]);
        } catch (...) {
          continue;
        }

        if (stop_id_map.find(stop_id) == stop_id_map.end()) {
          Node node;
          node.id = nodes.size();
          node.gtfs_stop_id = stop_id;
          node.stop_name = stop_name;
          node.lat = lat;
          node.lon = lon;
          stop_id_map[stop_id] = node.id;
          nodes.push_back(node);
        }
      }
    }
    std::cout << "[Graph] Loaded " << nodes.size() << " stops." << std::endl;
  }

  struct StopTimeEntry {
    std::string trip_id, stop_id;
    int seq;
  };

  void loadStopTimes(const std::string &filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
      std::cerr << "[Error] Cannot open " << filename << std::endl;
      return;
    }
    std::string line;
    std::getline(file, line); // Header
    std::vector<StopTimeEntry> entries;

    while (std::getline(file, line)) {
      auto cols = parseCSVLine(line);
      if (cols.size() < 3)
        continue;

      StopTimeEntry e;
      e.trip_id = cols[0];
      e.stop_id = cols[1];
      try {
        e.seq = std::stoi(cols[2]);
      } catch (...) {
        continue;
      }
      if (stop_id_map.count(e.stop_id))
        entries.push_back(e);
    }

    // Sort: TripID -> Sequence
    std::sort(entries.begin(), entries.end(),
              [](const StopTimeEntry &a, const StopTimeEntry &b) {
                if (a.trip_id != b.trip_id)
                  return a.trip_id < b.trip_id;
                return a.seq < b.seq;
              });

    int edgeCount = 0;
    for (size_t i = 1; i < entries.size(); ++i) {
      const auto &prev = entries[i - 1];
      const auto &curr = entries[i];

      if (prev.trip_id == curr.trip_id) {
        NodeID u = stop_id_map[prev.stop_id];
        NodeID v = stop_id_map[curr.stop_id];

        // Determine Mode
        int mode = BUS;
        if (trip_routes.count(prev.trip_id)) {
          std::string route_id = trip_routes[prev.trip_id];
          if (route_modes.count(route_id)) {
            mode = route_modes[route_id];
          }
        }

        // --- Physics-Based Weight ---
        double speed = AVG_BUS_SPEED_MPS;
        if (mode == METRO)
          speed = METRO_SPEED_MPS;
        if (mode == MICROBUS)
          speed = MICROBUS_SPEED_MPS;

        double dist =
            haversine(nodes[u].lat, nodes[u].lon, nodes[v].lat, nodes[v].lon);
        double timeWeight = (dist / speed) + STOP_DWELL_TIME;

        // Forward edge
        nodes[u].outgoing.push_back({v, timeWeight, prev.trip_id, mode});
        edgeCount++;

        // Microbus routes run both directions in Cairo —
        // add reverse edge so the sparse microbus network is traversable.
        if (mode == MICROBUS) {
          nodes[v].outgoing.push_back({u, timeWeight, prev.trip_id, mode});
          edgeCount++;
        }
      }
    }
    std::cout << "[Graph] Created " << edgeCount << " transit edges."
              << std::endl;
  }

  // Generate walking transfer edges between nearby stops.
  // Uses a spatial grid for O(n) performance instead of O(n²).
  void generateTransferEdges() {
    std::cout << "[Graph] Generating walking transfer edges (max "
              << MAX_WALK_DISTANCE << "m)..." << std::endl;
    int transferCount = 0;

    // --- Spatial Grid Index ---
    // Grid cell size ~MAX_WALK_DISTANCE in degrees (rough: 1° lat ≈ 111km)
    const double cellSize = MAX_WALK_DISTANCE / 111000.0; // in degrees
    std::unordered_map<long long, std::vector<NodeID>> grid;

    auto cellKey = [&](double lat, double lon) -> long long {
      int cx = (int)std::floor(lon / cellSize);
      int cy = (int)std::floor(lat / cellSize);
      return (long long)cy * 1000000LL + cx;
    };

    // Insert all nodes into grid
    for (size_t i = 0; i < nodes.size(); ++i) {
      grid[cellKey(nodes[i].lat, nodes[i].lon)].push_back((NodeID)i);
    }

    // For each node, check neighboring grid cells (3x3)
    for (size_t i = 0; i < nodes.size(); ++i) {
      int cx = (int)std::floor(nodes[i].lon / cellSize);
      int cy = (int)std::floor(nodes[i].lat / cellSize);

      for (int dx = -1; dx <= 1; ++dx) {
        for (int dy = -1; dy <= 1; ++dy) {
          long long key = (long long)(cy + dy) * 1000000LL + (cx + dx);
          auto it = grid.find(key);
          if (it == grid.end())
            continue;

          for (NodeID j : it->second) {
            if ((NodeID)i >= j)
              continue; // avoid duplicates

            double dist = haversine(nodes[i].lat, nodes[i].lon, nodes[j].lat,
                                    nodes[j].lon);
            if (dist <= MAX_WALK_DISTANCE && dist > 0) {
              double walkTime = dist / WALK_SPEED_MPS;

              nodes[i].outgoing.push_back({j, walkTime, "WALK", WALK});
              nodes[j].outgoing.push_back({(NodeID)i, walkTime, "WALK", WALK});
              transferCount++;
            }
          }
        }
      }
    }
    std::cout << "[Graph] Created " << transferCount
              << " walking transfer edges." << std::endl;
  }
};

RouteResult runAStar(GTFSGraph &graph, NodeID startNode, NodeID endNode,
                     int modeMask, double walkStart, double walkEnd,
                     double sLat, double sLon, double dLat, double dLon,
                     const std::string &typeLabel) {

  RouteResult result;
  result.type = typeLabel;
  result.totalDuration = 0;

  auto heuristic = [&](NodeID u) {
    double dist = haversine(graph.nodes[u].lat, graph.nodes[u].lon, dLat, dLon);
    return dist / MAX_SPEED_MPS;
  };

  std::vector<PathInfo> info(graph.nodes.size());
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

    for (const auto &edge : graph.nodes[top.u].outgoing) {
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
  std::vector<std::string> trips;
  NodeID curr = endNode;
  while (curr != -1) {
    path.push_back(curr);
    trips.push_back(info[curr].trip_id);
    curr = info[curr].parent;
  }
  std::reverse(path.begin(), path.end());

  // 1. Initial Walking Segment (from user origin to first stop)
  result.segments.push_back({sLon, sLat, "Origin", graph.nodes[path[0]].lon,
                             graph.nodes[path[0]].lat,
                             graph.nodes[path[0]].stop_name, "walking", 0});

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

        result.segments.push_back({graph.nodes[u].lon, graph.nodes[u].lat,
                                   graph.nodes[u].stop_name, graph.nodes[v].lon,
                                   graph.nodes[v].lat, graph.nodes[v].stop_name,
                                   mode, count});
        startIdx = i;
      }
    }
  }

  // 3. Final Walking Segment (from last stop to user destination)
  result.segments.push_back({graph.nodes[endNode].lon, graph.nodes[endNode].lat,
                             graph.nodes[endNode].stop_name, dLon, dLat,
                             "Destination", "walking", 0});

  return result;
}

int main() {
  GTFSGraph graph;

  // Auto-detect data path
  std::vector<std::string> searchPaths = {".",
                                          "c:/Users/Hp/CLionProjects/Waslny"};
  std::string dataPath = "";
  for (const auto &path : searchPaths) {
    std::ifstream f(path + "/stops.csv");
    if (f.good()) {
      dataPath = path;
      break;
    }
  }

  if (dataPath.empty()) {
    std::cerr << "Error: Could not locate GTFS data.\n";
    return 1;
  }

  graph.loadGTFS(dataPath);

  // --- Read user coordinates from input.txt ---
  std::ifstream infile(dataPath + "/input.txt");
  if (!infile.is_open()) {
    std::cerr << "Error: input.txt not found.\n";
    return 1;
  }
  std::string line;
  double sLat, sLon, dLat, dLon;
  auto readCoord = [&](double &lat, double &lon) {
    if (std::getline(infile, line)) {
      std::replace(line.begin(), line.end(), ',', ' ');
      std::stringstream ss(line);
      ss >> lat >> lon;
    }
  };
  readCoord(sLat, sLon);
  readCoord(dLat, dLon);
  infile.close();

  std::cout << "[Input] Source:      " << std::fixed << std::setprecision(6)
            << sLat << ", " << sLon << std::endl;
  std::cout << "[Input] Destination: " << dLat << ", " << dLon << std::endl;

  // Find nearest graph nodes to user coordinates
  NodeID start = graph.findNearestNode(sLat, sLon);
  NodeID end = graph.findNearestNode(dLat, dLon);

  std::ofstream outfile(dataPath + "/output.json");

  // Helper: escape JSON strings (for Arabic stop names)
  auto jsonEscape = [](const std::string &s) -> std::string {
    std::string result;
    for (char c : s) {
      switch (c) {
      case '"':
        result += "\\\"";
        break;
      case '\\':
        result += "\\\\";
        break;
      case '\n':
        result += "\\n";
        break;
      case '\r':
        result += "\\r";
        break;
      case '\t':
        result += "\\t";
        break;
      default:
        result += c;
      }
    }
    return result;
  };

  if (start != -1 && end != -1) {
    double w1 =
        haversine(sLat, sLon, graph.nodes[start].lat, graph.nodes[start].lon);
    double w2 =
        haversine(dLat, dLon, graph.nodes[end].lat, graph.nodes[end].lon);

    std::cout << "[Info] Nearest start stop: " << graph.nodes[start].stop_name
              << " (" << w1 << "m away)" << std::endl;
    std::cout << "[Info] Nearest end stop:   " << graph.nodes[end].stop_name
              << " (" << w2 << "m away)" << std::endl;

    // Run all 4 route searches — WALK is included so walking transfer
    // edges can be used even in single-mode searches
    std::vector<RouteResult> results;
    results.push_back(runAStar(graph, start, end, BUS | WALK, w1, w2, sLat,
                               sLon, dLat, dLon, "bus_only"));
    results.push_back(runAStar(graph, start, end, METRO | WALK, w1, w2, sLat,
                               sLon, dLat, dLon, "metro_only"));
    results.push_back(runAStar(graph, start, end, MICROBUS | WALK, w1, w2, sLat,
                               sLon, dLat, dLon, "microbus_only"));
    results.push_back(runAStar(graph, start, end, ANY | WALK, w1, w2, sLat,
                               sLon, dLat, dLon, "optimal"));

    outfile << std::fixed << std::setprecision(6);
    outfile << "{\n";
    outfile << "  \"query\": {\n";
    outfile << "    \"origin\": { \"lat\": " << sLat << ", \"lon\": " << sLon
            << " },\n";
    outfile << "    \"destination\": { \"lat\": " << dLat
            << ", \"lon\": " << dLon << " }\n";
    outfile << "  },\n";
    outfile << "  \"routes\": [\n";

    for (size_t ri = 0; ri < results.size(); ++ri) {
      const auto &r = results[ri];
      bool found = (r.totalDuration < INF);

      outfile << "    {\n";
      outfile << "      \"type\": \"" << r.type << "\",\n";
      outfile << "      \"found\": " << (found ? "true" : "false") << ",\n";

      if (found) {
        int totalSec = (int)(r.totalDuration);
        int totalMin = totalSec / 60;
        int remSec = totalSec % 60;
        outfile << "      \"totalDurationSeconds\": " << totalSec << ",\n";
        outfile << "      \"totalDurationFormatted\": \"" << totalMin << " min "
                << remSec << " sec\",\n";
        outfile << "      \"totalSegments\": " << r.segments.size() << ",\n";
        outfile << "      \"segments\": [\n";

        for (size_t si = 0; si < r.segments.size(); ++si) {
          const auto &seg = r.segments[si];
          double segDist =
              haversine(seg.startLat, seg.startLon, seg.endLat, seg.endLon);
          double segSpeed = WALK_SPEED_MPS;
          if (seg.method == "bus")
            segSpeed = AVG_BUS_SPEED_MPS;
          if (seg.method == "metro")
            segSpeed = METRO_SPEED_MPS;
          if (seg.method == "microbus")
            segSpeed = MICROBUS_SPEED_MPS;
          int segDuration = (segDist > 0) ? (int)(segDist / segSpeed) : 0;

          outfile << "        {\n";
          outfile << "          \"startLocation\": {\n";
          outfile << "            \"lat\": " << seg.startLat << ",\n";
          outfile << "            \"lon\": " << seg.startLon << ",\n";
          outfile << "            \"name\": \"" << jsonEscape(seg.startName)
                  << "\"\n";
          outfile << "          },\n";
          outfile << "          \"endLocation\": {\n";
          outfile << "            \"lat\": " << seg.endLat << ",\n";
          outfile << "            \"lon\": " << seg.endLon << ",\n";
          outfile << "            \"name\": \"" << jsonEscape(seg.endName)
                  << "\"\n";
          outfile << "          },\n";
          outfile << "          \"method\": \"" << seg.method << "\",\n";
          outfile << "          \"numStops\": " << seg.numStops << ",\n";
          outfile << "          \"distanceMeters\": " << (int)segDist << ",\n";
          outfile << "          \"durationSeconds\": " << segDuration << "\n";
          outfile << "        }" << (si < r.segments.size() - 1 ? "," : "")
                  << "\n";
        }

        outfile << "      ]\n";
      } else {
        outfile << "      \"totalDurationSeconds\": null,\n";
        outfile << "      \"totalDurationFormatted\": null,\n";
        outfile << "      \"totalSegments\": 0,\n";
        outfile << "      \"segments\": []\n";
      }

      outfile << "    }" << (ri < results.size() - 1 ? "," : "") << "\n";
    }

    outfile << "  ]\n";
    outfile << "}\n";

    // Print summary to console
    std::cout << "\n=== Route Results ===" << std::endl;
    for (const auto &r : results) {
      if (r.totalDuration < INF) {
        std::cout << r.type << ": " << (int)(r.totalDuration / 60) << " min, "
                  << r.segments.size() << " segments" << std::endl;
      } else {
        std::cout << r.type << ": No path found" << std::endl;
      }
    }
  } else {
    outfile << "{ \"error\": \"Could not resolve coordinates to stops\" }\n";
  }
  outfile.close();
  std::cout << "\nResults written to " << dataPath << "/output.json"
            << std::endl;

  return 0;
}
