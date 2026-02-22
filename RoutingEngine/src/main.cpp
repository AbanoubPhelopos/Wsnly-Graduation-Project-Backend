#include <iostream>
#include <string>
#include <cstdlib>

#include "graph.hpp"
#include "service_impl.hpp"
#include <grpcpp/grpcpp.h>

using grpc::Server;
using grpc::ServerBuilder;

void RunServer() {
  std::string server_address("0.0.0.0:50051");

  // Initialize Graph with GTFS data
  Graph graph;

  // Try to load GTFS from standard locations or env var
  std::string gtfsPath = "GTFS"; // Default
  if (const char *env_p = std::getenv("GTFS_PATH")) {
    gtfsPath = env_p;
  }

  graph.loadGTFS(gtfsPath);

  if (graph.GetNodes().empty()) {
    std::cerr << "Failed to load GTFS data from: " << gtfsPath << std::endl;
    std::cerr << "Ensure GTFS_PATH points to a folder containing stops/routes/trips/stop_times CSV or TXT files." << std::endl;
    std::exit(1);
  }

  RoutingServiceImpl service(graph);

  ServerBuilder builder;
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  builder.RegisterService(&service);

  std::unique_ptr<Server> server(builder.BuildAndStart());
  std::cout << "Server listening on " << server_address << std::endl;
  std::cout << "Graph loaded with " << graph.GetNodes().size() << " nodes."
            << std::endl;

  server->Wait();
}

int main(int argc, char **argv) {
  RunServer();
  return 0;
}
