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


LOCATION_ALIASES = {
    "الف مسكن": "ألف مسكن",
    "الالف مسكن": "ألف مسكن",
    "عباسيه": "العباسية",
    "العباسيه": "العباسية",
    "سرايا القيه": "سرايا القبة",
    "سرايا القبه": "سرايا القبة",
    "السرايا القيه": "سرايا القبة",
    "السرايا القبه": "سرايا القبة",
    "شيرتون": "شيراتون",
}

KNOWN_LOCATION_COORDINATES = {
    "ألف مسكن": (30.1188972, 31.3400652),
    "الف مسكن": (30.1188972, 31.3400652),
    "الالف مسكن": (30.1188972, 31.3400652),
    "العباسية": (30.0727858, 31.2840893),
    "العباسيه": (30.0727858, 31.2840893),
    "ميدان العباسية": (30.0650075, 31.2714452),
}


def _normalize_text(value: str) -> str:
    text = (value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _clean_location_candidate(value: str) -> str:
    candidate = _normalize_text(value)
    candidate = re.sub(
        r"^(?:اركب\s+ايه\s+علشان|عايز\s+اركب\s+ايه\s+علشان|عايز|عايزة|عاوزه|اريد|محتاج|حابب|لو سمحت|ممكن|اروح|اذهب|روح|علشان|عشان|ازاي|ازاى|اوصل|اوصل)\s+",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    if " في " in candidate:
        before_in, after_in = candidate.rsplit(" في ", 1)
        if any(
            token in before_in
            for token in ("عند", "بيت", "شغل", "مكان", "منطقة", "ناحية", "جنب")
        ):
            candidate = after_in

    candidate = re.sub(r"^(?:اروح|اذهب|روح)\s+", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+(?:لو سمحت|من فضلك)$", "", candidate, flags=re.IGNORECASE)
    return candidate.strip(" ,.-")


def _apply_alias(location_name: str) -> str:
    normalized = _normalize_text(location_name)
    return LOCATION_ALIASES.get(normalized, normalized)


def _resolve_known_coordinates(location_name: str):
    normalized = _normalize_text(location_name).replace("،", "")
    return KNOWN_LOCATION_COORDINATES.get(normalized)


def _extract_with_rules(text: str):
    normalized = _normalize_text(text)

    patterns = [
        re.compile(r"^من\s+(?P<from>.+?)\s+(?:الى|إلى)\s+(?P<to>.+)$", re.IGNORECASE),
        re.compile(
            r"^(?:عايز|عايزة|عاوزه|اريد|محتاج|حابب)?\s*(?:اروح|اذهب|روح)?\s*(?P<to>.+?)\s+من\s+(?P<from>.+)$",
            re.IGNORECASE,
        ),
        re.compile(r"^from\s+(?P<from>.+?)\s+to\s+(?P<to>.+)$", re.IGNORECASE),
        re.compile(r"^to\s+(?P<to>.+?)\s+from\s+(?P<from>.+)$", re.IGNORECASE),
    ]

    for pattern in patterns:
        match = pattern.search(normalized)
        if not match:
            continue

        origin = _clean_location_candidate(match.group("from"))
        destination = _clean_location_candidate(match.group("to"))
        if origin and destination:
            return _apply_alias(origin), _apply_alias(destination)

    # Conversational pattern: destination first + explicit current location.
    convo = re.search(
        r"(?:اروح|اذهب|روح)\s+(?:ازاي\s+|ازاى\s+)?(?P<to>.+?)\s+(?:و\s*انا|وانا)\s+في\s+(?P<from>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if convo:
        origin = _clean_location_candidate(convo.group("from"))
        destination = _clean_location_candidate(convo.group("to"))
        if origin and destination:
            return _apply_alias(origin), _apply_alias(destination)

    # Destination-only request. Source can be supplied by API current_location.
    destination_only = re.search(
        r"(?:عايز|عايزة|عاوزه|اريد|محتاج|حابب)?\s*(?:اروح|اذهب|روح)\s+(?P<to>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if destination_only:
        destination = _clean_location_candidate(destination_only.group("to"))
        destination = re.sub(r"\s+(?:و\s*انا.*)$", "", destination, flags=re.IGNORECASE)
        if destination:
            return "", _apply_alias(destination)

    if " من " in normalized:
        before_from, after_from = normalized.rsplit(" من ", 1)
        origin = _clean_location_candidate(after_from)
        destination = ""

        if " الى " in before_from:
            destination = _clean_location_candidate(before_from.split(" الى ")[-1])
        elif " إلى " in before_from:
            destination = _clean_location_candidate(before_from.split(" إلى ")[-1])
        else:
            tokens = before_from.strip().split()
            destination = _clean_location_candidate(tokens[-1] if tokens else "")

        if origin and destination:
            return _apply_alias(origin), _apply_alias(destination)

    return "", ""


def extract_locations(text):
    if nlp_pipeline is not None:
        results = nlp_pipeline(text)
        from_loc_name = ""
        to_loc_name = ""

        for entity in results:
            label = (entity.get("entity_group") or entity.get("entity") or "").upper()
            word = _clean_location_candidate(entity.get("word", "").replace("##", ""))

            if not word:
                continue

            if "FROM" in label:
                from_loc_name = word
            elif "TO" in label:
                to_loc_name = word

        if from_loc_name and to_loc_name:
            return _apply_alias(from_loc_name), _apply_alias(to_loc_name)

    return _extract_with_rules(text)


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

        if not to_loc_name:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("could not extract destination from text")
            return pb2.RouteResponse(intent="unknown")

        logger.info(f"📍 Extracted: From '{from_loc_name}' To '{to_loc_name}'")

        # 3. Geocode
        from_coords = None
        if from_loc_name:
            from_coords = _resolve_known_coordinates(
                from_loc_name
            ) or geocoder.get_coordinates(from_loc_name)
        to_coords = _resolve_known_coordinates(to_loc_name) or geocoder.get_coordinates(
            to_loc_name
        )

        if not to_coords:
            logger.warning("❌ Geocoding failed for one or more locations.")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("could not geocode destination location")
            return pb2.RouteResponse(
                from_location=from_loc_name,
                to_location=to_loc_name,
                intent="unknown",
            )

        logger.info(f"🌍 Coordinates: {from_coords} -> {to_coords}")

        response = pb2.RouteResponse(
            from_location=from_loc_name,
            to_location=to_loc_name,
            intent="standard",
        )
        if from_coords:
            response.from_coordinates.CopyFrom(
                pb2.Location(latitude=from_coords[0], longitude=from_coords[1])
            )
        response.to_coordinates.CopyFrom(
            pb2.Location(latitude=to_coords[0], longitude=to_coords[1])
        )
        return response


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
