# Ai-Service (NLP + Geocoding)

Ai-Service is a Python gRPC microservice that converts natural language trip requests into structured locations and coordinates.

## Responsibilities

- Parse free-form text (Arabic/English) to detect origin and destination.
- Handle conversational Arabic patterns and common typo aliases for Cairo locations.
- Geocode extracted places to latitude/longitude using Google Maps.
- Return interpretation result to Wslny API over gRPC.

Ai-Service does not calculate paths. Routing is delegated to `RoutingEngine`.

The service may return destination coordinates even when origin is missing (destination-only request); API can complete source using `current_location`.

## Communication Contract

- Service: `TransitInterpreter`
- RPC: `ExtractRoute(RouteRequest) -> RouteResponse`
- Proto source: `shared/protos/interpreter.proto`

```text
Wslny API --gRPC--> Ai-Service
Ai-Service --gRPC response (locations + coordinates)--> Wslny API
```

## Why This Separation Matters

- Keeps NLP complexity isolated from pathfinding code.
- Lets map-pin requests skip AI entirely for lower latency.
- Allows independent scaling/tuning of model and geocoder behavior.

## Input/Output Example

Input text:

```json
{ "text": "عايز اروح العباسيه من مسكن" }
```

Output (gRPC payload conceptually):

```json
{
  "from_location": "مسكن",
  "to_location": "العباسية",
  "from_coordinates": { "latitude": 30.0, "longitude": 31.0 },
  "to_coordinates": { "latitude": 30.0, "longitude": 31.0 },
  "intent": "standard"
}
```

Destination-only example:

```json
{
  "from_location": "",
  "to_location": "شيراتون",
  "to_coordinates": { "latitude": 30.10, "longitude": 31.37 },
  "intent": "standard"
}
```

## Caching

Geocoding results are cached in-memory in `geocoder.py` to reduce external API calls for repeated place names.

## Accuracy Strategy

- ML pipeline when a valid model exists in `TransitModel`.
- Rule-based extraction fallback for robust runtime behavior.
- Alias normalization for frequent user typos and colloquial names.
- Regression tests in `Ai-Service/tests/test_flow.py` for critical Arabic phrases.

## Required Environment

- `GOOGLE_MAPS_API_KEY`

## Run

Recommended via root compose:

```bash
docker compose up --build
```

Standalone build/run:

```bash
docker build -f Ai-Service/Dockerfile -t ai-service .
docker run -p 50052:50052 -e GOOGLE_MAPS_API_KEY=... ai-service
```
