#include "pathfinder.hpp"
#include <algorithm>
#include <limits>
#include <queue>
#include <vector>

struct KeyVal {
  NodeID u;
  double val;
  bool operator>(const KeyVal &other) const { return val > other.val; }
};

PathResult Pathfinder::FindPath(const Graph &graph, NodeID startInfo,
                                NodeID endInfo) {
  PathResult result;
  result.found = false;
  result.total_distance = 0;
  result.total_duration = 0;

  const auto &nodes = graph.GetNodes();
  if (startInfo < 0 || startInfo >= (int)nodes.size() || endInfo < 0 ||
      endInfo >= (int)nodes.size()) {
    return result;
  }

  const double INF = std::numeric_limits<double>::max();
  std::vector<double> dist(nodes.size(), INF);
  std::vector<NodeID> parent(nodes.size(), -1);
  std::vector<const Edge *> parent_edge(nodes.size(), nullptr);

  std::priority_queue<KeyVal, std::vector<KeyVal>, std::greater<KeyVal>> pq;

  dist[startInfo] = 0;
  pq.push({startInfo, 0});

  while (!pq.empty()) {
    KeyVal top = pq.top();
    pq.pop();

    if (top.val > dist[top.u])
      continue;

    if (top.u == endInfo) {
      break;
    }

    const Node &uNode = nodes[top.u];
    for (const auto &edge : uNode.outgoing) {
      if (dist[top.u] + edge.weight < dist[edge.to]) {
        dist[edge.to] = dist[top.u] + edge.weight;
        parent[edge.to] = top.u;
        parent_edge[edge.to] = &edge;
        pq.push({edge.to, dist[edge.to]});
      }
    }
  }

  if (dist[endInfo] < INF) {
    result.found = true;
    result.total_duration = dist[endInfo];

    NodeID curr = endInfo;
    while (curr != -1) {
      result.path_nodes.push_back(curr);
      if (curr != startInfo && parent[curr] != -1) {
        if (parent_edge[curr]) {
          result.path_edges.push_back(*parent_edge[curr]);
        }
      }
      curr = parent[curr];
    }
    std::reverse(result.path_nodes.begin(), result.path_nodes.end());
    std::reverse(result.path_edges.begin(), result.path_edges.end());
  }

  return result;
}
