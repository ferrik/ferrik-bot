"""
🌐 API для Telegram Mini App
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
import hmac
import hashlib
import json
from urllib.parse import parse_qs
from datetime import datetime

from app.services.sheets_service import sheets_service
from app.utils.validators import safe_parse_price, validate_phone, normalize_phone

router = APIRouter(prefix="/api/v1", tags=["miniapp"])

# ============================================================================
# SECURITY: Верифікація Telegram initData
# ============================================================================

def verify_telegram_webapp_data(init_data: str, bot_token: str) -> bool:
    """
    Перевіряє автентичність даних від Telegram WebApp
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = parse_qs(init_data)
        hash_value = parsed.get('hash', [''])[0]
        
        # Видаляємо hash з даних
        data_check_string = '\n'.join(
            f"{k}={v[0]}" for k, v in sorted(parsed.items()) if k != 'hash'
        )
        
        # Обчислюємо secret key
        secret_key = hmac.new(
            "WebAppData".encode(),
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Перевіряємо підпис
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == hash_value
    except Exception as e:
        logger.error(f"❌ Telegram data verification failed: {e}")
        return False


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check для Mini App API"""
    return {"ok": True, "status": "alive", "service": "miniapp_api"}


@router.get("/menu")
async def get_menu(
    restaurant: Optional[str] = None,
    category: Optional[str] = None,
    active: bool = True,
    limit: int = 100,
    offset: int = 0
):
    """
    Отримати повне меню або з фільтрами
    
    Query params:
    - restaurant: фільтр по ресторану (ID партнера)
    - category: фільтр по категорії
    - active: тільки активні товари (default: True)
    - limit: максимум результатів
    - offset: пропустити N записів
    """
    try:
        # Отримати з Google Sheets
        all_items = sheets_service.get_menu()
        
        # Фільтрація
        filtered = all_items
        
        if active:
            filtered = [i for i in filtered if str(i.get('Активний', '')).upper() == 'TRUE']
        
        if restaurant:
            filtered = [i for i in filtered if i.get('Ресторан') == restaurant]
        
        if category:
            filtered = [i for i in filtered if i.get('Категорія') == category]
        
        # Pagination
        paginated = filtered[offset:offset+limit]
        
        # Форматування відповіді
        result = []
        for item in paginated:
            result.append({
                "id": item.get('ID'),
                "category": item.get('Категорія'),
                "name": item.get('Страва'),
                "description": item.get('Опис', ''),
                "price": safe_parse_price(item.get('Ціна', 0)),
                "restaurant": item.get('Ресторан'),
                "time_delivery": int(item.get('Час_доставки_хв', 30)),
                "photo_url": item.get('Фото_URL', ''),
                "active": str(item.get('Активний', '')).upper() == 'TRUE',
                "cook_time": int(item.get('Час_приготування_хв', 15)),
                "allergens": item.get('Алергени', ''),
                "rating": float(item.get('Рейтинг', 0)),
                "mood_tags": [tag.strip() for tag in str(item.get('Mood_Tags', '')).split(',') if tag.strip()]
            })
        
        return {
            "ok": True,
            "data": result,
            "total": len(filtered),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching menu: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch menu")


@router.get("/menu/mood/{tag}")
async def get_menu_by_mood(tag: str):
    """
    Отримати товари по mood тегу
    
    Приклади: calm, energy, party, romantic, movie, spicy
    """
    try:
        all_items = sheets_service.get_menu()
        
        # Фільтрація по mood tags
        filtered = []
        for item in all_items:
            if str(item.get('Активний', '')).upper() != 'TRUE':
                continue
            
            mood_tags = str(item.get('Mood_Tags', '')).lower()
            if tag.lower() in mood_tags:
                filtered.append({
                    "id": item.get('ID'),
                    "category": item.get('Категорія'),
                    "name": item.get('Страва'),
                    "description": item.get('Опис', ''),
                    "price": safe_parse_price(item.get('Ціна', 0)),
                    "restaurant": item.get('Ресторан'),
                    "photo_url": item.get('Фото_URL', ''),
                    "rating": float(item.get('Рейтинг', 0)),
                    "mood_tags": [t.strip() for t in str(item.get('Mood_Tags', '')).split(',') if t.strip()]
                })
        
        return {
            "ok": True,
            "mood": tag,
            "data": filtered,
            "count": len(filtered)
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching mood menu: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch mood menu")


@router.get("/restaurants")
async def get_restaurants(active: bool = True):
    """Отримати список партнерів (ресторанів)"""
    try:
        partners = sheets_service.get_partners()
        
        result = []
        for p in partners:
            if active and p.get('Статус') != 'Активний':
                continue
            
            result.append({
                "id": p.get('ID'),
                "name": p.get('Назва_партнера'),
                "category": p.get('Категорія'),
                "rating": float(p.get('Рейтинг', 0)),
                "commission_pct": float(p.get('Комісія_%', 0)),
                "status": p.get('Статус'),
                "phone": p.get('Телефон', '')
            })
        
        return {"ok": True, "data": result}
        
    except Exception as e:
        logger.error(f"❌ Error fetching restaurants: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch restaurants")


@router.post("/order")
async def create_order(order_data: dict):
    """
    Створити замовлення (записати в Google Sheets)
    
    Request body:
    {
      "user": {"telegram_user_id": 123, "name": "", "phone": "+380..."},
      "items": [{"id": "1", "name": "Маргарита", "price": 180, "quantity": 2, "restaurant": "FerrikPizza"}],
      "subtotal": 360,
      "delivery_cost": 50,
      "total": 410,
      "address": "вул. X",
      "delivery_type": "delivery",
      "payment_method": "cash",
      "note": "",
      "promo_code": ""
    }
    """
    try:
        # Валідація
        user = order_data.get('user', {})
        items = order_data.get('items', [])
        
        if not user.get('telegram_user_id'):
            raise HTTPException(status_code=400, detail="Missing telegram_user_id")
        
        if not items:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        phone = user.get('phone', '')
        if not validate_phone(phone):
            raise HTTPException(status_code=400, detail="Invalid phone number")
        
        # Генерувати ID замовлення
        now = datetime.now()
        order_id = f"ORD_{now.strftime('%Y%m%d_%H%M%S')}_{user['telegram_user_id']}"
        
        # Підготувати дані для Google Sheets
        order_row = {
            'ID_Замовлення': order_id,
            'Telegram_User_ID': user['telegram_user_id'],
            'Час_Замовлення': now.strftime('%Y-%m-%d %H:%M:%S'),
            'Товари_JSON': json.dumps(items, ensure_ascii=False),
            'Загальна_Сума': order_data.get('total', 0),
            'Адреса': order_data.get('address', ''),
            'Телефон': normalize_phone(phone),
            'Спосіб_Оплати': order_data.get('payment_method', 'cash'),
            'Статус': 'Новий',
            'Канал': 'Mini App',
            'Вартість_доставки': order_data.get('delivery_cost', 0),
            'Тип_доставки': order_data.get('delivery_type', 'delivery'),
            'Примітки': order_data.get('note', ''),
            'Промокод': order_data.get('promo_code', '')
        }
        
        # Зберегти в Google Sheets
        sheets_service.save_order(order_row)
        
        # ETA розрахунок (беремо максимальний час з товарів)
        eta_minutes = max([item.get('time_delivery', 30) for item in items], default=30)
        
        return {
            "ok": True,
            "order_id": order_id,
            "status": "created",
            "eta_minutes": eta_minutes,
            "message": "Замовлення успішно створено! 🎉"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating order: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order")


@router.get("/orders/user/{telegram_user_id}")
async def get_user_orders(telegram_user_id: int, limit: int = 10):
    """Отримати історію замовлень користувача"""
    try:
        orders = sheets_service.get_user_orders(telegram_user_id, limit=limit)
        
        result = []
        for order in orders:
            result.append({
                "order_id": order.get('ID_Замовлення'),
                "created_at": order.get('Час_Замовлення'),
                "total": safe_parse_price(order.get('Загальна_Сума')),
                "status": order.get('Статус'),
                "items_count": len(json.loads(order.get('Товари_JSON', '[]')))
            })
        
        return {"ok": True, "data": result}
        
    except Exception as e:
        logger.error(f"❌ Error fetching user orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.post("/promo/validate")
async def validate_promo(promo_data: dict):
    """
    Перевірити промокод
    
    Request: {"code": "WELCOME10"}
    Response: {"ok": true, "discount_pct": 10, "valid": true}
    """
    try:
        code = promo_data.get('code', '').strip().upper()
        
        if not code:
            raise HTTPException(status_code=400, detail="Promo code is required")
        
        # Отримати промокоди з Sheets
        promos = sheets_service.get_promo_codes()
        
        for promo in promos:
            if promo.get('Код', '').upper() == code:
                # Перевірити статус
                if promo.get('Статус') != 'Активний':
                    return {"ok": False, "valid": False, "message": "Промокод неактивний"}
                
                # Перевірити ліміт
                used = int(promo.get('Використано', 0))
                limit = int(promo.get('Ліміт_використань', 999))
                
                if used >= limit:
                    return {"ok": False, "valid": False, "message": "Промокод вичерпано"}
                
                # Перевірити дату
                valid_until = promo.get('Дійсний_до', '')
                if valid_until:
                    # TODO: перевірка дати
                    pass
                
                return {
                    "ok": True,
                    "valid": True,
                    "code": code,
                    "discount_pct": float(promo.get('Знижка_%', 0)),
                    "message": f"Промокод застосовано! Знижка {promo.get('Знижка_%')}%"
                }
        
        return {"ok": False, "valid": False, "message": "Промокод не знайдено"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error validating promo: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate promo code")
