# Use a lightweight Python image
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the model files and code
COPY my_transit_model/ ./my_transit_model/
COPY protos/ ./protos/
COPY server.py .

# Generate gRPC code inside the container
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. protos/interpreter.proto

# Expose the gRPC port
EXPOSE 50051

# Start the service
CMD ["python", "server.py"]