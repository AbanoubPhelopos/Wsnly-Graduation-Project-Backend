import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock grpc modules before import Server
sys.modules["grpc"] = MagicMock()
sys.modules["protos.interpreter_pb2"] = MagicMock()
sys.modules["protos.interpreter_pb2_grpc"] = MagicMock()
sys.modules["googlemaps"] = MagicMock()
sys.modules["transformers"] = MagicMock()

# Mock Geocoding
with patch("geocoder.GoogleMapsGeocoder") as MockGeocoder:
    # Import Server after mocking
    from Server import TransitInterpreterService

    class TestTransitFlow(unittest.TestCase):
        def setUp(self):
            self.service = TransitInterpreterService()
            # Mock the internal services of the instance
            pass

        @patch("Server.geocoder")
        @patch("Server.nlp_pipeline")
        def test_extract_route_success(self, mock_pipeline, mock_geocoder):
            # Setup Mocks (Arabic Entities)
            mock_pipeline.return_value = [
                {"entity_group": "FROM", "word": "الدقي"},
                {"entity_group": "TO", "word": "المعادي"},
            ]

            mock_geocoder.get_coordinates.side_effect = [
                (30.038, 31.21),  # Dokki
                (29.96, 31.25),  # Maadi
            ]

            # Create Request
            mock_request = MagicMock()
            mock_request.text = "عايز اروح من الدقي للمعادي"

            # Run
            response = self.service.ExtractRoute(mock_request, None)

            # Verify
            self.assertEqual(response.from_location, "الدقي")
            self.assertEqual(response.to_location, "المعادي")

            # Verify Calls
            mock_geocoder.get_coordinates.assert_any_call("الدقي")
            mock_geocoder.get_coordinates.assert_any_call("المعادي")


if __name__ == "__main__":
    unittest.main()
