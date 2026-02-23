import os
import sys

# --- STEP 1: FIX PATHS FIRST ---
# This must happen before importing any generated proto files
current_dir = os.path.dirname(os.path.abspath(__file__))
protos_path = os.path.join(current_dir, "protos")
sys.path.append(protos_path)

import grpc
from concurrent import futures
from transformers import pipeline
import logging
import re

# --- STEP 2: IMPORT PROTOS ---
# Now that 'protos' is in the path, these imports will work
import interpreter_pb2 as pb2
import interpreter_pb2_grpc as pb2_grpc

from geocoder import GoogleMapsGeocoder

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Load the Model ONE TIME at startup
NER_MODEL_PATH = "./TransitModel"

print("🚀 Loading AI Model... this may take a moment.")
nlp_pipeline = None
try:
    nlp_pipeline = pipeline(
        "token-classification",
        model=NER_MODEL_PATH,
        tokenizer=NER_MODEL_PATH,
        aggregation_strategy="simple",
    )
    print("✅ Model Loaded!")
except Exception as error:
    logger.warning(f"Model load failed, using rule-based fallback extractor: {error}")


def extract_locations(text):
    if nlp_pipeline is not None:
        results = nlp_pipeline(text)
        from_loc_name = ""
        to_loc_name = ""
        for entity in results:
            if entity.get("entity_group") == "FROM":
                from_loc_name = entity.get("word", "")
            elif entity.get("entity_group") == "TO":
                to_loc_name = entity.get("word", "")
        return from_loc_name.strip(), to_loc_name.strip()

    normalized = " ".join((text or "").strip().split())

    match_en = re.search(r"to\s+(.+?)\s+from\s+(.+)$", normalized, flags=re.IGNORECASE)
    if match_en:
        return match_en.group(2).strip(), match_en.group(1).strip()

    if " من " in normalized:
        before_from, after_from = normalized.rsplit(" من ", 1)
        origin = after_from.strip()
        destination = ""

        if " الى " in before_from:
            destination = before_from.split(" الى ")[-1].strip()
        elif " إلى " in before_from:
            destination = before_from.split(" إلى ")[-1].strip()
        else:
            tokens = before_from.strip().split()
            destination = tokens[-1].strip() if tokens else ""

        return origin, destination

    return "", ""


# Initialize Services
geocoder = GoogleMapsGeocoder()


class TransitInterpreterService(pb2_grpc.TransitInterpreterServicer):
    def ExtractRoute(self, request, context):
        text = (request.text or "").strip()
        if not text:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("text is required")
            return pb2.RouteResponse()

        logger.info(f"📩 Received request: {text}")

        from_loc_name, to_loc_name = extract_locations(text)

        if not from_loc_name or not to_loc_name:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("could not extract origin and destination from text")
            return pb2.RouteResponse(intent="unknown")

        logger.info(f"📍 Extracted: From '{from_loc_name}' To '{to_loc_name}'")

        # 3. Geocode
        from_coords = geocoder.get_coordinates(from_loc_name)
        to_coords = geocoder.get_coordinates(to_loc_name)

        if not from_coords or not to_coords:
            logger.warning("❌ Geocoding failed for one or more locations.")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("could not geocode one or more locations")
            return pb2.RouteResponse(
                from_location=from_loc_name,
                to_location=to_loc_name,
                intent="unknown",
            )

        logger.info(f"🌍 Coordinates: {from_coords} -> {to_coords}")

        # 5. Return gRPC Response
        # Create Location objects if coordinates exist
        from_loc_msg = None
        if from_coords:
            from_loc_msg = pb2.Location(
                latitude=from_coords[0], longitude=from_coords[1]
            )

        to_loc_msg = None
        if to_coords:
            to_loc_msg = pb2.Location(latitude=to_coords[0], longitude=to_coords[1])

        return pb2.RouteResponse(
            from_location=from_loc_name,
            to_location=to_loc_name,
            from_coordinates=from_loc_msg,
            to_coordinates=to_loc_msg,
            intent="standard",
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_TransitInterpreterServicer_to_server(
        TransitInterpreterService(), server
    )
    server.add_insecure_port("[::]:50052")
    print("🌍 AI Interpreter Service running on port 50052...")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
