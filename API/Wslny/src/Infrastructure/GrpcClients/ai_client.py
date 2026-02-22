import grpc
import sys
from pathlib import Path
from typing import Any, Dict, Optional

STUBS_DIR = Path(__file__).resolve().parent / "stubs"
if str(STUBS_DIR) not in sys.path:
    sys.path.append(str(STUBS_DIR))

try:
    import interpreter_pb2  # type: ignore
    import interpreter_pb2_grpc  # type: ignore
except ImportError:
    interpreter_pb2 = None
    interpreter_pb2_grpc = None


class AiGrpcClientError(Exception):
    def __init__(self, code: Any, details: str):
        super().__init__(details)
        self.code = code
        self.details = details


class AiGrpcClient:
    def __init__(self, host="ai-service", port=50052, timeout_seconds=5.0):
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.timeout_seconds = timeout_seconds

        if interpreter_pb2_grpc is None:
            raise RuntimeError("interpreter gRPC stubs are not generated")

        self.stub = interpreter_pb2_grpc.TransitInterpreterStub(self.channel)

    def extract_route(self, text: str) -> Optional[Dict[str, Any]]:
        if interpreter_pb2 is None:
            raise RuntimeError("interpreter gRPC stubs are not generated")

        request = interpreter_pb2.RouteRequest(text=text)
        try:
            response = self.stub.ExtractRoute(request, timeout=self.timeout_seconds)

            if response.HasField("from_coordinates") and response.HasField(
                "to_coordinates"
            ):
                return {
                    "from_lat": response.from_coordinates.latitude,
                    "from_lon": response.from_coordinates.longitude,
                    "to_lat": response.to_coordinates.latitude,
                    "to_lon": response.to_coordinates.longitude,
                    "from_location": response.from_location,
                    "to_location": response.to_location,
                    "intent": response.intent,
                }
            return None
        except grpc.RpcError as error:
            code = error.code() if hasattr(error, "code") else grpc.StatusCode.UNKNOWN
            details = (
                error.details()
                if hasattr(error, "details")
                else "AI service call failed"
            )
            raise AiGrpcClientError(code=code, details=details) from error
