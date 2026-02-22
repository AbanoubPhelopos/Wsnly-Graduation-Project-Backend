import grpc
import sys
import os

# Add protos to path just like Server.py
current_dir = os.path.dirname(os.path.abspath(__file__))
protos_path = os.path.join(current_dir, 'protos')
sys.path.append(protos_path)

import interpreter_pb2
import interpreter_pb2_grpc

def run():
    print("🚀 Sending request to AI Service at localhost:50052...")
    
    # Connect to the local Docker container mapped port
    channel = grpc.insecure_channel('localhost:50052')
    stub = interpreter_pb2_grpc.TransitInterpreterStub(channel)
    
    # Test Request
    text_input = "عايز اروح من الدقي للمعادي"
    print(f"📝 Input: {text_input}")
    
    try:
        response = stub.ExtractRoute(interpreter_pb2.RouteRequest(text=text_input))
        
        print(f"\n✅ Response Received!")
        print(f"📍 From: {response.from_location} ({response.from_coordinates.latitude}, {response.from_coordinates.longitude})")
        print(f"📍 To: {response.to_location} ({response.to_coordinates.latitude}, {response.to_coordinates.longitude})")
        print(f"📏 Distance: {response.total_distance_meters} meters")
        print(f"⏱️ Duration: {response.total_duration_seconds} seconds")
        print(f"Steps: {len(response.steps)}")
        
        for i, step in enumerate(response.steps):
            print(f"  {i+1}. {step.instruction} ({step.distance_meters}m, {step.duration_seconds}s)")
            
    except grpc.RpcError as e:
        print(f"\n❌ RPC Failed: {e.code()}")
        print(f"Details: {e.details()}")

if __name__ == '__main__':
    run()
