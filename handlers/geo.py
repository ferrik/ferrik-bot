from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import logging

logger = logging.getLogger("ferrik")
geolocator = Nominatim(user_agent="ferrikfoot_bot")
RESTAURANT_LOCATION = (49.553517, 25.594767)  # Тернопіль
DELIVERY_RADIUS_KM = 7

def check_delivery_availability(address):
    try:
        location = geolocator.geocode(address + ", Тернопіль")
        if not location:
            logger.warning(f"Geocode failed for address: {address}")
            return None
        user_location = (location.latitude, location.longitude)
        distance = geodesic(RESTAURANT_LOCATION, user_location).kilometers
        if distance <= DELIVERY_RADIUS_KM:
            logger.info(f"Delivery available for address: {address}, distance: {distance:.2f} km")
            return user_location
        else:
            logger.info(f"Delivery not available for address: {address}, distance: {distance:.2f} km")
            return None
    except Exception as e:
        logger.error(f"Error checking delivery availability for {address}: {e}")
        return None
