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
        self.channel = grpc.insecure_channel(f"{host}:{port}")
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
            details = (
                error.details()
                if hasattr(error, "details")
                else "Routing service call failed"
            )
            raise RoutingGrpcClientError(code=code, details=details) from error
