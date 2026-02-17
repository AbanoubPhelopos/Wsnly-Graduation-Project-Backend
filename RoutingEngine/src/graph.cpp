#include "graph.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>


// Existing methods
void Graph::AddNode(NodeID id, const std::string &name, double lat,
                    double lon) {
  if (id >= nodes_.size()) {
    nodes_.resize(id + 1);
  }
  nodes_[id] = {id, name, "", lat, lon, {}};
}

void Graph::AddEdge(NodeID from, NodeID to, Weight weight,
                    const std::string &type, const std::string &line_name) {
  if (from >= nodes_.size() || to >= nodes_.size())
    return;
  nodes_[from].outgoing.push_back({to, weight, "", type, line_name});
}

NodeID Graph::FindNearestNode(double lat, double lon) const {
  NodeID nearest = -1;
  double minDistance = INF;

  for (const auto &node : nodes_) {
    // Euclidean distance for simplicity (valid for small areas like Cairo)
    // Or use Haversine if needed. Keeping it simple as per original code.
    double dLat = node.lat - lat;
    double dLon = node.lon - lon;
    double dist = std::sqrt(dLat * dLat + dLon * dLon);

    if (dist < minDistance) {
      minDistance = dist;
      nearest = node.id;
    }
  }
  return nearest;
}

const Node *Graph::GetNode(NodeID id) const {
  if (id < 0 || id >= nodes_.size())
    return nullptr;
  return &nodes_[id];
}

const std::vector<Node> &Graph::GetNodes() const { return nodes_; }

// --- GTFS Loading Implementations ---

std::string Graph::clean(std::string s) {
  if (s.empty())
    return s;
  if (s.size() >= 2 && s.front() == '"' && s.back() == '"') {
    s = s.substr(1, s.size() - 2);
  }
  s.erase(0, s.find_first_not_of(" \t\r\n"));
  s.erase(s.find_last_not_of(" \t\r\n") + 1);
  return s;
}

double Graph::parseTime(const std::string &timeStr) {
  if (timeStr.empty())
    return -1.0;
  int h, m, s;
  char d1, d2;
  std::stringstream ss(timeStr);
  ss >> h >> d1 >> m >> d2 >> s;
  if (ss.fail())
    return 0.0;
  return h * 3600.0 + m * 60.0 + s;
}

void Graph::loadGTFS(const std::string &folderPath) {
  std::cout << "Loading GTFS from " << folderPath << "..." << std::endl;
  loadAgencies(folderPath + "/agency.txt"); // Try .txt first (standard)
  loadRoutes(folderPath + "/routes.txt");
  loadTrips(folderPath + "/trips.txt");
  loadStops(folderPath + "/stops.txt");
  loadStopTimes(folderPath + "/stop_times.txt");

  // Also try .csv if .txt failed (simple fallback check handled by ifstream
  // failure in sub-functions)
  if (nodes_.empty()) {
    loadAgencies(folderPath + "/agency.csv");
    loadRoutes(folderPath + "/routes.csv");
    loadTrips(folderPath + "/trips.csv");
    loadStops(folderPath + "/stops.csv");
    loadStopTimes(folderPath + "/stop_times.csv");
  }

  std::cout << "Graph built: " << nodes_.size() << " nodes." << std::endl;
}

void Graph::loadAgencies(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
  std::string line;
  std::getline(file, line);
  while (std::getline(file, line)) {
    line = clean(line);
    std::stringstream ss(line);
    std::string segment;
    std::vector<std::string> cols;
    while (std::getline(ss, segment, ','))
      cols.push_back(clean(segment));

    if (cols.size() >= 2) {
      Agency a;
      a.id = cols[0];
      a.name = cols[1];
      agencies[a.id] = a;
    }
  }
}

void Graph::loadRoutes(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
  std::string line;
  std::getline(file, line);
  while (std::getline(file, line)) {
    line = clean(line);
    std::stringstream ss(line);
    std::string segment;
    std::vector<std::string> cols;
    while (std::getline(ss, segment, ','))
      cols.push_back(clean(segment));

    if (cols.size() >= 4) {
      Route r;
      r.id = cols[0];
      r.agency_id = cols[1];
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

void Graph::loadTrips(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
  std::string line;
  std::getline(file, line);
  while (std::getline(file, line)) {
    line = clean(line);
    std::stringstream ss(line);
    std::string segment;
    std::vector<std::string> cols;
    while (std::getline(ss, segment, ','))
      cols.push_back(clean(segment));

    if (cols.size() >= 3) {
      Trip t;
      t.route_id = cols[0];
      t.service_id = cols[1];
      t.id = cols[2];
      trips[t.id] = t;
    }
  }
}

void Graph::loadStops(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
  std::string line;
  std::getline(file, line);

  while (std::getline(file, line)) {
    line = clean(line);
    std::stringstream ss(line);
    std::string segment;
    std::vector<std::string> cols;
    while (std::getline(ss, segment, ','))
      cols.push_back(clean(segment));

    if (cols.size() >= 2) {
      std::string stop_id = cols[0];
      std::string stop_name = cols[1];
      double lat = 0.0;
      double lon = 0.0;

      // Standard GTFS: stop_lat is index 4, stop_lon is index 5
      // Assuming columns: stop_id, stop_code, stop_name, stop_desc, stop_lat,
      // stop_lon, ... Adjust indices based on typical simple CSVs if needed,
      // but let's try standard first. If cols are fewer, we might have a
      // simplified CSV.

      if (cols.size() >= 6) {
        try {
          lat = std::stod(cols[4]);
          lon = std::stod(cols[5]);
        } catch (...) {
        }
      } else if (cols.size() >= 4) {
        // Maybe: id, name, lat, lon
        try {
          lat = std::stod(cols[2]);
          lon = std::stod(cols[3]);
        } catch (...) {
        }
      }

      if (stop_id_map.find(stop_id) == stop_id_map.end()) {
        Node node;
        node.id = (int)nodes_.size();
        node.gtfs_stop_id = stop_id;
        node.name = stop_name;
        node.lat = lat;
        node.lon = lon;

        stop_id_map[stop_id] = node.id;
        stop_name_map[stop_name] = node.id;
        nodes_.push_back(node);
      }
    }
  }
}

struct StopTimeEntry {
  std::string trip_id;
  std::string stop_id;
  int seq;
  double arrival;
  double departure;
};

void Graph::loadStopTimes(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open())
    return;
  std::string line;
  std::getline(file, line);

  std::vector<StopTimeEntry> entries;

  while (std::getline(file, line)) {
    line = clean(line);
    std::stringstream ss(line);
    std::string segment;
    std::vector<std::string> cols;
    while (std::getline(ss, segment, ','))
      cols.push_back(clean(segment));

    // trip_id, stop_id, stop_sequence, arrival_time, departure_time
    if (cols.size() < 5)
      continue;

    StopTimeEntry entry;
    entry.trip_id = cols[0];
    entry.stop_id = cols[1];
    try {
      entry.seq = std::stoi(cols[2]);
    } catch (...) {
      continue;
    }
    entry.arrival = parseTime(cols[3]);
    entry.departure = parseTime(cols[4]);

    if (stop_id_map.find(entry.stop_id) != stop_id_map.end()) {
      entries.push_back(entry);
    }
  }

  std::sort(entries.begin(), entries.end(),
            [](const StopTimeEntry &a, const StopTimeEntry &b) {
              if (a.trip_id != b.trip_id)
                return a.trip_id < b.trip_id;
              return a.seq < b.seq;
            });

  for (size_t i = 1; i < entries.size(); ++i) {
    const auto &prev = entries[i - 1];
    const auto &curr = entries[i];

    if (prev.trip_id == curr.trip_id) {
      NodeID u = stop_id_map[prev.stop_id];
      NodeID v = stop_id_map[curr.stop_id];
      double w = curr.arrival - prev.departure;
      if (w < 0)
        w = 0;

      // Inferred types/line name (optional, could be cleaned up later)
      std::string type = "BUS";
      std::string lineName = "Route";

      std::string tripId = prev.trip_id;
      if (trips.count(tripId)) {
        std::string routeId = trips[tripId].route_id;
        if (routes.count(routeId)) {
          lineName = routes[routeId].short_name;
          // crude mapping
          if (routes[routeId].type == 1)
            type = "METRO";
        }
      }

      nodes_[u].outgoing.push_back({v, w, tripId, type, lineName});
    }
  }
}

NodeID Graph::getNodeId(const std::string &query) const {
  if (stop_id_map.find(query) != stop_id_map.end())
    return stop_id_map.at(query);
  if (stop_name_map.find(query) != stop_name_map.end())
    return stop_name_map.at(query);

  // partial search
  for (auto &pair : stop_name_map) {
    if (pair.first.find(query) != std::string::npos)
      return pair.second;
  }
  return -1;
}
