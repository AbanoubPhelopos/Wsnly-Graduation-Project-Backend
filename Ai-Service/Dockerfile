FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for grpc
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY Ai-Service/Requirements.txt .
RUN pip install --no-cache-dir -r Requirements.txt

# Copy Code
COPY Ai-Service/TransitModel/ ./TransitModel/
COPY Ai-Service/Server.py .
COPY Ai-Service/geocoder.py .

# Copy Proto definitions
COPY Ai-Service/protos/ ./protos/

# Generate gRPC Code
RUN python -m grpc_tools.protoc -I./protos --python_out=./protos --grpc_python_out=./protos ./protos/interpreter.proto

# Set PYTHONPATH to include current directory
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 50052

CMD ["python", "Server.py"]
