# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Generate gRPC stubs during image build
RUN mkdir -p /app/src/Infrastructure/GrpcClients/stubs \
    && touch /app/src/Infrastructure/GrpcClients/stubs/__init__.py \
    && python -m grpc_tools.protoc -I./protos --python_out=./src/Infrastructure/GrpcClients/stubs --grpc_python_out=./src/Infrastructure/GrpcClients/stubs ./protos/interpreter.proto ./protos/routing.proto

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose port (adjust if needed)
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# Run gunicorn (or manage.py runserver for dev)
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "Wslny.src.Presentation.wsgi:application"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
