import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _FakeStatusCode:
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"


class _FakeLocation:
    def __init__(self, latitude=0.0, longitude=0.0):
        self.latitude = latitude
        self.longitude = longitude


class _FakeRouteResponse:
    def __init__(self, **kwargs):
        self.from_location = kwargs.get("from_location", "")
        self.to_location = kwargs.get("to_location", "")
        self.from_coordinates = kwargs.get("from_coordinates", _FakeLocation())
        self.to_coordinates = kwargs.get("to_coordinates", _FakeLocation())
        self.intent = kwargs.get("intent", "")
        self.steps = kwargs.get("steps", [])
        self.total_distance_meters = kwargs.get("total_distance_meters", 0.0)
        self.total_duration_seconds = kwargs.get("total_duration_seconds", 0.0)


fake_grpc = types.ModuleType("grpc")
setattr(fake_grpc, "StatusCode", _FakeStatusCode)

fake_pb2 = types.ModuleType("interpreter_pb2")
setattr(fake_pb2, "Location", _FakeLocation)
setattr(fake_pb2, "RouteResponse", _FakeRouteResponse)

fake_pb2_grpc = types.ModuleType("interpreter_pb2_grpc")
setattr(fake_pb2_grpc, "TransitInterpreterServicer", object)

sys.modules["grpc"] = fake_grpc
sys.modules["interpreter_pb2"] = fake_pb2
sys.modules["interpreter_pb2_grpc"] = fake_pb2_grpc
sys.modules["googlemaps"] = MagicMock()
sys.modules["transformers"] = MagicMock()


with patch("geocoder.GoogleMapsGeocoder"):
    import Server


class TestTransitFlow(unittest.TestCase):
    def setUp(self):
        self.service = Server.TransitInterpreterService()

    @patch("Server.nlp_pipeline", None)
    def test_extract_locations_phrase_abbasia_from_alf_maskan(self):
        origin, destination = Server.extract_locations("عايز اروح العباسيه من الف مسكن")
        self.assertEqual(origin, "ألف مسكن")
        self.assertEqual(destination, "العباسية")

    @patch("Server.nlp_pipeline", None)
    def test_extract_locations_phrase_taggamoa_from_ramsis(self):
        origin, destination = Server.extract_locations(
            "اركب ايه علشان اروح التجمع من رمسيس"
        )
        self.assertEqual(origin, "رمسيس")
        self.assertEqual(destination, "التجمع")

    @patch("Server.nlp_pipeline", None)
    def test_known_coordinate_resolution(self):
        self.assertEqual(
            Server._resolve_known_coordinates("الف مسكن"), (30.1188972, 31.3400652)
        )
        self.assertEqual(
            Server._resolve_known_coordinates("العباسية"), (30.0727858, 31.2840893)
        )

    @patch("Server.nlp_pipeline", None)
    @patch("Server.geocoder")
    def test_extract_route_uses_known_coordinates_without_geocoder(self, mock_geocoder):
        mock_request = types.SimpleNamespace(text="عايز اروح العباسيه من الف مسكن")
        mock_context = MagicMock()

        response = self.service.ExtractRoute(mock_request, mock_context)

        self.assertEqual(response.from_location, "ألف مسكن")
        self.assertEqual(response.to_location, "العباسية")
        self.assertAlmostEqual(response.from_coordinates.latitude, 30.1188972)
        self.assertAlmostEqual(response.to_coordinates.latitude, 30.0727858)
        self.assertFalse(mock_geocoder.get_coordinates.called)


if __name__ == "__main__":
    unittest.main()
