import grpc
import sys
from pathlib import Path
from typing import Any, Dict, Optional

STUBS_DIR = Path(__file__).resolve().parent / "stubs"
if str(STUBS_DIR) not in sys.path:
    sys.path.append(str(STUBS_DIR))

try:
    import routing_pb2  # type: ignore
    import routing_pb2_grpc  # type: ignore
except ImportError:
    routing_pb2 = None
    routing_pb2_grpc = None


class RoutingGrpcClientError(Exception):
    def __init__(self, code: Any, details: str):
        super().__init__(details)
        self.code = code
        self.details = details


class RoutingGrpcClient:
    def __init__(self, host="routing-engine", port=50051, timeout_seconds=10.0):
        options = [
            ('grpc.keepalive_time_ms', 60000),
            ('grpc.keepalive_timeout_ms', 20000),
            ('grpc.keepalive_permit_without_calls', 1),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_ping_interval_without_data_ms', 10000)
        ]

        if str(port) == "443":
            credentials = grpc.ssl_channel_credentials()
            self.channel = grpc.secure_channel(f"{host}:{port}", credentials, options=options)
        else:
            self.channel = grpc.insecure_channel(f"{host}:{port}", options=options)
        self.timeout_seconds = timeout_seconds

        if routing_pb2_grpc is None:
            raise RuntimeError("routing gRPC stubs are not generated")

        self.stub = routing_pb2_grpc.RoutingServiceStub(self.channel)

    def get_route(
        self, sLat: float, sLon: float, dLat: float, dLon: float, mode: str = "optimal"
    ) -> Optional[Dict[str, Any]]:
        if routing_pb2 is None:
            raise RuntimeError("routing gRPC stubs are not generated")

        origin = routing_pb2.Point(latitude=sLat, longitude=sLon)
        destination = routing_pb2.Point(latitude=dLat, longitude=dLon)

        request = routing_pb2.RouteRequest(
            origin=origin, destination=destination, mode=mode
        )

        try:
            response = self.stub.GetRoute(request, timeout=self.timeout_seconds)

            if response.routes:
                result = {
                    "query": {
                        "origin": {
                            "lat": response.query.origin.latitude,
                            "lon": response.query.origin.longitude,
                        },
                        "destination": {
                            "lat": response.query.destination.latitude,
                            "lon": response.query.destination.longitude,
                        },
                    },
                    "routes": [],
                }

                for route in response.routes:
                    route_data = {
                        "type": route.type,
                        "found": route.found,
                        "totalDurationSeconds": route.total_duration_seconds,
                        "totalDurationFormatted": route.total_duration_formatted,
                        "totalSegments": route.total_segments,
                        "totalDistanceMeters": route.total_distance_meters,
                        "segments": [],
                    }

                    for segment in route.segments:
                        route_data["segments"].append(
                            {
                                "startLocation": {
                                    "lat": segment.start_location.latitude,
                                    "lon": segment.start_location.longitude,
                                    "name": segment.start_name,
                                },
                                "endLocation": {
                                    "lat": segment.end_location.latitude,
                                    "lon": segment.end_location.longitude,
                                    "name": segment.end_name,
                                },
                                "method": segment.method,
                                "numStops": segment.num_stops,
                                "distanceMeters": segment.distance_meters,
                                "durationSeconds": segment.duration_seconds,
                            }
                        )

                    result["routes"].append(route_data)

                return result

            result = {
                "total_distance_meters": response.total_distance_meters,
                "total_duration_seconds": response.total_duration_seconds,
                "steps": [],
            }

            for step in response.steps:
                result["steps"].append(
                    {
                        "instruction": step.instruction,
                        "distance_meters": step.distance_meters,
                        "duration_seconds": step.duration_seconds,
                        "type": step.type,
                        "line_name": step.line_name,
                        "start_location": {
                            "lat": step.start_location.latitude,
                            "lon": step.start_location.longitude,
                        },
                        "end_location": {
                            "lat": step.end_location.latitude,
                            "lon": step.end_location.longitude,
                        },
                    }
                )

            return result

        except grpc.RpcError as error:
            code = error.code() if hasattr(error, "code") else grpc.StatusCode.UNKNOWN
            details = "Routing service call failed"
            if hasattr(error, "details") and error.details():
                details = str(error.details())
            raise RoutingGrpcClientError(code=code, details=details) from error
