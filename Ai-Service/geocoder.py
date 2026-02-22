import googlemaps
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleMapsGeocoder:
    def __init__(self, api_key=None):
        if not api_key:
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        
        if not api_key:
            logger.warning("No Google Maps API Key provided. Geocoding will fail.")
            self.client = None
        else:
            self.client = googlemaps.Client(key=api_key)
            logger.info("Google Maps Client initialized.")
        
        self.cache = {}

    def get_coordinates(self, location_name):
        """
        Resolves a location name to (latitude, longitude).
        Returns None if not found or error.
        """
        if not self.client:
            logger.error("Google Maps Client not initialized.")
            return None

        # Check cache
        if location_name in self.cache:
            logger.info(f"Cache hit for '{location_name}'")
            return self.cache[location_name]

        try:
            # Egypt specific bias and Arabic language preference
            geocode_result = self.client.geocode(location_name, components={'country': 'EG'}, language='ar')

            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                
                logger.info(f"Geocoded '{location_name}' to ({lat}, {lng})")
                self.cache[location_name] = (lat, lng)
                return (lat, lng)
            else:
                logger.warning(f"No results found for '{location_name}'")
                return None

        except Exception as e:
            logger.error(f"Geocoding error for '{location_name}': {e}")
            return None
