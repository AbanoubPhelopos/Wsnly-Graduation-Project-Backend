#include "graph.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>

// --- CSV Parsing Implementation ---

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

// --- Graph Method Implementations ---

NodeID Graph::findNearestNode(double lat, double lon) const {
  NodeID bestNode = -1;
  double minDist = INF;
  for (const auto &node : nodes_) {
    double dist = haversine(lat, lon, node.lat, node.lon);
    if (dist < minDist) {
      minDist = dist;
      bestNode = node.id;
    }
  }
  return bestNode;
}

NodeID Graph::findNearestNode(double lat, double lon, int modeMask) const {
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
  for (const auto &node : nodes_) {
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

const Node *Graph::GetNode(NodeID id) const {
  if (id < 0 || id >= (int)nodes_.size())
    return nullptr;
  return &nodes_[id];
}

const std::vector<Node> &Graph::GetNodes() const { return nodes_; }

std::string Graph::getTripMode(const std::string &trip_id) const {
  if (trip_id == "WALK")
    return "walking";
  auto tr = trip_routes.find(trip_id);
  if (tr != trip_routes.end()) {
    auto rm = route_modes.find(tr->second);
    if (rm != route_modes.end()) {
      return modeToString(rm->second);
    }
  }
  return "unknown";
}

// --- GTFS Loading ---

void Graph::loadGTFS(const std::string &folderPath) {
  std::cout << "[Graph] Loading GTFS Data from " << folderPath << "..."
            << std::endl;

  // Try .csv first (project default), then .txt (GTFS standard)
  loadRoutes(folderPath + "/routes.csv");
  loadTrips(folderPath + "/trips.csv");
  loadStops(folderPath + "/stops.csv");
  loadStopTimes(folderPath + "/stop_times.csv");

  if (nodes_.empty()) {
    loadRoutes(folderPath + "/routes.txt");
    loadTrips(folderPath + "/trips.txt");
    loadStops(folderPath + "/stops.txt");
    loadStopTimes(folderPath + "/stop_times.txt");
  }

  generateTransferEdges();

  std::cout << "[Graph] Loaded " << nodes_.size() << " stops." << std::endl;
}

void Graph::loadRoutes(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
  std::string line;
  std::getline(file, line); // Header
  while (std::getline(file, line)) {
    auto cols = parseCSVLine(line);
    if (cols.size() >= 2) {
      std::string route_id = cols[0];
      std::string agency_id = cols[1];

      int mode = BUS; // default
      if (agency_id == "M_CAI-METRO")
        mode = METRO;
      else if (agency_id == "MB_CAI_BUS")
        mode = MICROBUS;
      else if (agency_id == "B1_CAI_BUS")
        mode = BUS;

      route_modes[route_id] = mode;

      // Also store in routes map if enough columns
      if (cols.size() >= 4) {
        Route r;
        r.id = route_id;
        r.agency_id = agency_id;
        r.short_name = cols[2];
        try {
          r.type = std::stoi(cols[3]);
        } catch (...) {
          r.type = 3;
        }
        routes[r.id] = r;
      }
    }
  }
  std::cout << "[Graph] Loaded " << route_modes.size() << " routes."
            << std::endl;
}

void Graph::loadTrips(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
  std::string line;
  std::getline(file, line); // Header
  while (std::getline(file, line)) {
    auto cols = parseCSVLine(line);
    if (cols.size() >= 3) {
      std::string route_id = cols[0];
      std::string trip_id = cols[2];
      trip_routes[trip_id] = route_id;

      Trip t;
      t.route_id = route_id;
      t.service_id = cols[1];
      t.id = trip_id;
      trips[t.id] = t;
    }
  }
  std::cout << "[Graph] Loaded " << trip_routes.size() << " trips."
            << std::endl;
}

void Graph::loadStops(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
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
        node.id = (int)nodes_.size();
        node.gtfs_stop_id = stop_id;
        node.stop_name = stop_name;
        node.lat = lat;
        node.lon = lon;
        stop_id_map[stop_id] = node.id;
        stop_name_map[stop_name] = node.id;
        nodes_.push_back(node);
      }
    }
  }
  std::cout << "[Graph] Loaded " << nodes_.size() << " stops." << std::endl;
}

struct StopTimeEntry {
  std::string trip_id, stop_id;
  int seq;
};

void Graph::loadStopTimes(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
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
          haversine(nodes_[u].lat, nodes_[u].lon, nodes_[v].lat, nodes_[v].lon);
      double timeWeight = (dist / speed) + STOP_DWELL_TIME;

      // Forward edge
      nodes_[u].outgoing.push_back({v, timeWeight, prev.trip_id, mode});
      edgeCount++;

      // Microbus routes run both directions in Cairo
      if (mode == MICROBUS) {
        nodes_[v].outgoing.push_back({u, timeWeight, prev.trip_id, mode});
        edgeCount++;
      }
    }
  }
  std::cout << "[Graph] Created " << edgeCount << " transit edges."
            << std::endl;
}

void Graph::generateTransferEdges() {
  std::cout << "[Graph] Generating walking transfer edges (max "
            << MAX_WALK_DISTANCE << "m)..." << std::endl;
  int transferCount = 0;

  // --- Spatial Grid Index ---
  const double cellSize = MAX_WALK_DISTANCE / 111000.0; // degrees
  std::unordered_map<long long, std::vector<NodeID>> grid;

  auto cellKey = [&](double lat, double lon) -> long long {
    int cx = (int)std::floor(lon / cellSize);
    int cy = (int)std::floor(lat / cellSize);
    return (long long)cy * 1000000LL + cx;
  };

  // Insert all nodes into grid
  for (size_t i = 0; i < nodes_.size(); ++i) {
    grid[cellKey(nodes_[i].lat, nodes_[i].lon)].push_back((NodeID)i);
  }

  // For each node, check neighboring grid cells (3x3)
  for (size_t i = 0; i < nodes_.size(); ++i) {
    int cx = (int)std::floor(nodes_[i].lon / cellSize);
    int cy = (int)std::floor(nodes_[i].lat / cellSize);

    for (int dx = -1; dx <= 1; ++dx) {
      for (int dy = -1; dy <= 1; ++dy) {
        long long key = (long long)(cy + dy) * 1000000LL + (cx + dx);
        auto it = grid.find(key);
        if (it == grid.end())
          continue;

        for (NodeID j : it->second) {
          if ((NodeID)i >= j)
            continue; // avoid duplicates

          double dist = haversine(nodes_[i].lat, nodes_[i].lon, nodes_[j].lat,
                                  nodes_[j].lon);
          if (dist <= MAX_WALK_DISTANCE && dist > 0) {
            double walkTime = dist / WALK_SPEED_MPS;

            nodes_[i].outgoing.push_back({j, walkTime, "WALK", WALK});
            nodes_[j].outgoing.push_back({(NodeID)i, walkTime, "WALK", WALK});
            transferCount++;
          }
        }
      }
    }
  }
  std::cout << "[Graph] Created " << transferCount << " walking transfer edges."
            << std::endl;
}

NodeID Graph::getNodeId(const std::string &query) const {
  auto it1 = stop_id_map.find(query);
  if (it1 != stop_id_map.end())
    return it1->second;
  auto it2 = stop_name_map.find(query);
  if (it2 != stop_name_map.end())
    return it2->second;

  // partial search
  for (const auto &pair : stop_name_map) {
    if (pair.first.find(query) != std::string::npos)
      return pair.second;
  }
  return -1;
}
