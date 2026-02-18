import os
import sys

# --- STEP 1: FIX PATHS FIRST ---
# This must happen before importing any generated proto files
current_dir = os.path.dirname(os.path.abspath(__file__))
protos_path = os.path.join(current_dir, 'protos')
sys.path.append(protos_path)

import grpc
from concurrent import futures
from transformers import pipeline
import logging

# --- STEP 2: IMPORT PROTOS ---
# Now that 'protos' is in the path, these imports will work
import interpreter_pb2 as pb2
import interpreter_pb2_grpc as pb2_grpc

from geocoder import GoogleMapsGeocoder
from routing_client import RoutingClient

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Load the Model ONE TIME at startup
NER_MODEL_PATH = "./TransitModel"

print("🚀 Loading AI Model... this may take a moment.")
nlp_pipeline = pipeline(
    "token-classification", 
    model=NER_MODEL_PATH, 
    tokenizer=NER_MODEL_PATH, 
    aggregation_strategy="simple"
)
print("✅ Model Loaded!")

# Initialize Services
geocoder = GoogleMapsGeocoder() 
routing_service_addr = os.getenv('ROUTING_SERVICE_ADDRESS', 'routing-engine:50051')
routing_client = RoutingClient(address=routing_service_addr)

class TransitInterpreterService(pb2_grpc.TransitInterpreterServicer):
    def ExtractRoute(self, request, context):
        text = request.text
        logger.info(f"📩 Received request: {text}")

        # 2. Run Inference
        results = nlp_pipeline(text)
        
        from_loc_name = ""
        to_loc_name = ""
        
        for entity in results:
            if entity['entity_group'] == 'FROM':
                from_loc_name = entity['word']
            elif entity['entity_group'] == 'TO':
                to_loc_name = entity['word']
        
        logger.info(f"📍 Extracted: From '{from_loc_name}' To '{to_loc_name}'")

        # 3. Geocode
        from_coords = geocoder.get_coordinates(from_loc_name)
        to_coords = geocoder.get_coordinates(to_loc_name)
        
        route_steps = [] 
        total_dist = 0.0
        total_dur = 0.0

        if from_coords and to_coords:
            logger.info(f"🌍 Coordinates: {from_coords} -> {to_coords}")
            
            # 4. Call Routing Engine
            route_resp = routing_client.get_route(from_coords, to_coords)
            
            if route_resp:
                total_dist = route_resp.total_distance_meters
                total_dur = route_resp.total_duration_seconds
                
                for step in route_resp.steps:
                    new_step = pb2.RouteStep(
                        instruction=step.instruction,
                        distance_meters=step.distance_meters,
                        duration_seconds=step.duration_seconds,
                        type=step.type,
                        line_name=step.line_name
                    )
                    if step.HasField('start_location'):
                        new_step.start_location.latitude = step.start_location.latitude
                        new_step.start_location.longitude = step.start_location.longitude
                    
                    if step.HasField('end_location'):
                        new_step.end_location.latitude = step.end_location.latitude
                        new_step.end_location.longitude = step.end_location.longitude
                        
                    route_steps.append(new_step)
        else:
            logger.warning("❌ Geocoding failed for one or more locations.")

        # 5. Return gRPC Response
        # Create Location objects if coordinates exist
        from_loc_msg = None
        if from_coords:
            from_loc_msg = pb2.Location(latitude=from_coords[0], longitude=from_coords[1])
            
        to_loc_msg = None
        if to_coords:
            to_loc_msg = pb2.Location(latitude=to_coords[0], longitude=to_coords[1])

        return pb2.RouteResponse(
            from_location=from_loc_name,
            to_location=to_loc_name,
            from_coordinates=from_loc_msg,
            to_coordinates=to_loc_msg,
            steps=route_steps,
            total_distance_meters=total_dist,
            total_duration_seconds=total_dur
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_TransitInterpreterServicer_to_server(TransitInterpreterService(), server)
    server.add_insecure_port('[::]:50052')
    print("🌍 AI Interpreter Service running on port 50052...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()