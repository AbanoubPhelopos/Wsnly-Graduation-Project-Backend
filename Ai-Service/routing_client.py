import grpc
import logging
import protos.routing_pb2 as routing_pb2
import protos.routing_pb2_grpc as routing_pb2_grpc

# Configure logging
logger = logging.getLogger(__name__)

import os

class RoutingClient:
    def __init__(self, address=None):
        if address is None:
            address = os.getenv('ROUTING_SERVICE_ADDRESS', 'localhost:50051')
        self.address = address
        self.channel = None
        self.stub = None

    def connect(self):
        if not self.channel:
            self.channel = grpc.insecure_channel(self.address)
            self.stub = routing_pb2_grpc.RoutingServiceStub(self.channel)
            logger.info(f"Connected to Routing Engine at {self.address}")

    def get_route(self, origin_coords, dest_coords, mode="fastest"):
        """
        Call RoutingEngine.GetRoute
        origin_coords: (lat, lon) tuple
        dest_coords: (lat, lon) tuple
        mode: string
        Returns: RouteResponse object or None on error
        """
        try:
            self.connect()
            
            origin = routing_pb2.Point(latitude=origin_coords[0], longitude=origin_coords[1])
            destination = routing_pb2.Point(latitude=dest_coords[0], longitude=dest_coords[1])
            
            request = routing_pb2.RouteRequest(
                origin=origin,
                destination=destination,
                mode=mode
            )
            
            logger.info(f"Sending RouteRequest: {origin_coords} -> {dest_coords}")
            response = self.stub.GetRoute(request)
            logger.info("Received RouteResponse")
            return response

        except grpc.RpcError as e:
            logger.error(f"Routing Engine RPC failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling Routing Engine: {e}")
            return None

    def close(self):
        if self.channel:
            self.channel.close()
            self.channel = None
