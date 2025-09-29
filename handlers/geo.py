import logging
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def check_delivery_availability(chat_id: str, user_id: str, address: str):
    """
    Перевіряє доступність доставки за адресою.
    """
    logger.info(f"Checking delivery availability for user {user_id} at {address}")
    
    try:
        geolocator = Nominatim(user_agent="ferrik_bot")
        restaurant_location = geolocator.geocode("Київ, вул. Прикладна, 1")
        user_location = geolocator.geocode(address)
        
        if not restaurant_location or not user_location:
            tg_send_message(chat_id, "Не вдалося визначити адресу. Спробуйте ще раз.")
            return False
        
        distance = geodesic(
            (restaurant_location.latitude, restaurant_location.longitude),
            (user_location.latitude, user_location.longitude)
        ).kilometers
        
        # Наприклад, доставка доступна в межах 10 км
        max_delivery_distance = 10.0
        if distance <= max_delivery_distance:
            tg_send_message(chat_id, f"Доставка доступна! Відстань: {distance:.2f} км.")
            return True
        else:
            tg_send_message(chat_id, f"На жаль, доставка недоступна. Відстань: {distance:.2f} км.")
            return False
            
    except Exception as e:
        logger.error(f"Error checking delivery for {address}: {e}")
        tg_send_message(chat_id, "Помилка при перевірці адреси. Спробуйте ще раз.")
        return False