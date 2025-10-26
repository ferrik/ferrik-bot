"""
🔄 Сервіс синхронізації даних з Google Sheets в БД
"""
import logging
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SyncService:
    """Синхронізація Google Sheets → SQLite"""
    
    def __init__(self, db_connection, sheets_service):
        """
        Args:
            db_connection: SQLite підключення
            sheets_service: Модуль services.sheets
        """
        self.db = db_connection
        self.sheets = sheets_service
    
    def sync_menu_from_sheets(self) -> Dict[str, any]:
        """
        Синхронізувати меню з Google Sheets в БД
        
        Returns:
            Dict з результатом: {'success': bool, 'added': int, 'updated': int, 'errors': list}
        """
        result = {
            'success': False,
            'added': 0,
            'updated': 0,
            'deleted': 0,
            'errors': [],
            'total_items': 0
        }
        
        try:
            logger.info("🔄 Starting menu sync from Google Sheets...")
            
            # Завантажити з Sheets
            sheets_data = self.sheets.get_menu_from_sheet()
            result['total_items'] = len(sheets_data)
            
            if not sheets_data:
                logger.warning("⚠️ No menu items found in Google Sheets")
                result['errors'].append("No items in source")
                return result
            
            # Отримати існуючі ID з БД
            existing_ids = set()
            rows = self.db.execute("SELECT id FROM menu_items").fetchall()
            for row in rows:
                existing_ids.add(row[0])
            
            # ID з Sheets
            sheets_ids = set()
            
            # Синхронізувати кожен товар
            for item in sheets_data:
                try:
                    item_id = str(item.get('id', ''))
                    if not item_id:
                        result['errors'].append(f"Item without ID: {item.get('Назва', 'Unknown')}")
                        continue
                    
                    sheets_ids.add(item_id)
                    
                    # Парсити дані
                    name = item.get('Назва', 'Без назви')
                    price = self._parse_price(item.get('Ціна', 0))
                    category = item.get('Категорія', 'Інше')
                    description = item.get('Опис', '')
                    image_url = item.get('Фото', '')
                    available = item.get('Доступно', True)
                    
                    # Конвертувати available в boolean
                    if isinstance(available, str):
                        available = available.lower() not in ['ні', 'no', 'false', '0', 'немає']
                    
                    # Перевірити чи існує
                    if item_id in existing_ids:
                        # Оновити
                        self.db.execute("""
                            UPDATE menu_items 
                            SET name = ?, price = ?, category = ?, description = ?, 
                                image_url = ?, available = ?, updated_at = ?
                            WHERE id = ?
                        """, (name, price, category, description, image_url, available, datetime.now(), item_id))
                        result['updated'] += 1
                    else:
                        # Додати новий
                        self.db.execute("""
                            INSERT INTO menu_items (id, name, price, category, description, image_url, available)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (item_id, name, price, category, description, image_url, available))
                        result['added'] += 1
                
                except Exception as e:
                    error_msg = f"Error syncing item {item.get('id', 'unknown')}: {e}"
                    logger.error(f"❌ {error_msg}")
                    result['errors'].append(error_msg)
            
            # Видалити товари які більше немає в Sheets
            items_to_delete = existing_ids - sheets_ids
            if items_to_delete:
                placeholders = ','.join('?' * len(items_to_delete))
                self.db.execute(f"DELETE FROM menu_items WHERE id IN ({placeholders})", list(items_to_delete))
                result['deleted'] = len(items_to_delete)
                logger.info(f"🗑️ Deleted {result['deleted']} items not in Sheets")
            
            # Commit змін
            self.db.commit()
            
            result['success'] = True
            logger.info(
                f"✅ Menu sync completed: " +
                f"+{result['added']} added, " +
                f"~{result['updated']} updated, " +
                f"-{result['deleted']} deleted"
            )
            
            # Записати в лог
            self._log_sync('menu', 'success', result['total_items'])
            
        except Exception as e:
            error_msg = f"Sync failed: {e}"
            logger.error(f"❌ {error_msg}")
            result['errors'].append(error_msg)
            self._log_sync('menu', 'error', 0, error_msg)
        
        return result
    
    def get_menu_from_db(self) -> List[Dict]:
        """
        Завантажити меню з БД
        
        Returns:
            List[Dict] - список товарів
        """
        try:
            rows = self.db.execute("""
                SELECT id, name, price, category, description, image_url, available, sort_order
                FROM menu_items
                WHERE available = 1
                ORDER BY sort_order, category, name
            """).fetchall()
            
            menu_items = []
            for row in rows:
                menu_items.append({
                    'id': row[0],
                    'Назва': row[1],
                    'Ціна': row[2],
                    'Категорія': row[3],
                    'Опис': row[4],
                    'Фото': row[5],
                    'Доступно': bool(row[6]),
                    'sort_order': row[7]
                })
            
            logger.debug(f"📋 Loaded {len(menu_items)} items from DB")
            return menu_items
            
        except Exception as e:
            logger.error(f"❌ Error loading menu from DB: {e}")
            return []
    
    def get_last_sync_info(self) -> Optional[Dict]:
        """Отримати інформацію про останню синхронізацію"""
        try:
            row = self.db.execute("""
                SELECT sync_type, status, items_count, error_message, synced_at
                FROM sync_log
                WHERE sync_type = 'menu'
                ORDER BY synced_at DESC
                LIMIT 1
            """).fetchone()
            
            if row:
                return {
                    'type': row[0],
                    'status': row[1],
                    'items_count': row[2],
                    'error': row[3],
                    'synced_at': row[4]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting sync info: {e}")
            return None
    
    def _parse_price(self, value) -> float:
        """Безпечний парсинг ціни"""
        if value is None:
            return 0.0
        
        try:
            # Видалити текст і конвертувати
            clean = str(value).replace('грн', '').replace(' ', '').replace(',', '.').strip()
            return float(clean) if clean else 0.0
        except:
            return 0.0
    
    def _log_sync(self, sync_type: str, status: str, items_count: int, error_message: str = None):
        """Записати лог синхронізації"""
        try:
            self.db.execute("""
                INSERT INTO sync_log (sync_type, status, items_count, error_message)
                VALUES (?, ?, ?, ?)
            """, (sync_type, status, items_count, error_message))
            self.db.commit()
        except Exception as e:
            logger.error(f"❌ Error logging sync: {e}")


# ============================================================================
# Scheduler для автоматичної синхронізації
# ============================================================================

class MenuSyncScheduler:
    """Планувальник автоматичної синхронізації"""
    
    def __init__(self, sync_service, interval_minutes=30):
        """
        Args:
            sync_service: SyncService екземпляр
            interval_minutes: Інтервал синхронізації в хвилинах
        """
        self.sync_service = sync_service
        self.interval_minutes = interval_minutes
        self.last_sync = None
    
    def should_sync(self) -> bool:
        """Перевірити чи потрібна синхронізація"""
        if not self.last_sync:
            return True
        
        from datetime import datetime, timedelta
        now = datetime.now()
        return (now - self.last_sync) > timedelta(minutes=self.interval_minutes)
    
    def sync_if_needed(self) -> Optional[Dict]:
        """Синхронізувати якщо потрібно"""
        if self.should_sync():
            logger.info("⏰ Auto-sync triggered")
            result = self.sync_service.sync_menu_from_sheets()
            self.last_sync = datetime.now()
            return result
        return None