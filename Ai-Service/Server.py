import grpc
from concurrent import futures
from transformers import pipeline
import protos.interpreter_pb2 as pb2
import protos.interpreter_pb2_grpc as pb2_grpc

# 1. Load the Model ONE TIME at startup
# We point directly to the folder you uploaded
NER_MODEL_PATH = "./my_transit_model"

print("🚀 Loading AI Model... this may take a moment.")
# aggregation_strategy="simple" merges "B-LOC" and "I-LOC" tokens automatically
nlp_pipeline = pipeline(
    "token-classification", 
    model=NER_MODEL_PATH, 
    tokenizer=NER_MODEL_PATH, 
    aggregation_strategy="simple"
)
print("✅ Model Loaded!")

class TransitInterpreterService(pb2_grpc.TransitInterpreterServicer):
    def ExtractRoute(self, request, context):
        text = request.text
        print(f"📩 Received request: {text}")

        # 2. Run Inference
        results = nlp_pipeline(text)
        
        # 3. Parse Output
        # The pipeline returns list of dicts: [{'entity_group': 'FROM', 'word': 'Dokki', ...}]
        from_loc = ""
        to_loc = ""
        
        for entity in results:
            if entity['entity_group'] == 'FROM':
                from_loc = entity['word']
            elif entity['entity_group'] == 'TO':
                to_loc = entity['word']

        # 4. Return gRPC Response
        return pb2.RouteResponse(
            from_location=from_loc,
            to_location=to_loc,
            intent="standard" # Placeholder logic
        )

def serve():
    # Start gRPC server on port 50051
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_TransitInterpreterServicer_to_server(TransitInterpreterService(), server)
    server.add_insecure_port('[::]:50051')
    print("🌍 AI Interpreter Service running on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()