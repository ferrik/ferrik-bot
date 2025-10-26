-- ============================================================================
-- Міграція 002: Додати таблицю menu_items
-- ============================================================================
-- Дата: 2025-10-26
-- Опис: Зберігання меню в БД для швидкого доступу
-- ============================================================================

-- Таблиця товарів меню
CREATE TABLE IF NOT EXISTS menu_items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0),
    category TEXT,
    description TEXT,
    image_url TEXT,
    available BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Індекси для швидкого пошуку
CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);
CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(available);
CREATE INDEX IF NOT EXISTS idx_menu_sort ON menu_items(sort_order);

-- Таблиця історії синхронізації
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,  -- 'menu', 'orders', etc.
    status TEXT NOT NULL,      -- 'success', 'error'
    items_count INTEGER,
    error_message TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Тригер для автоматичного оновлення updated_at
CREATE TRIGGER IF NOT EXISTS update_menu_items_timestamp 
AFTER UPDATE ON menu_items
BEGIN
    UPDATE menu_items SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- View для активних товарів
CREATE VIEW IF NOT EXISTS active_menu_items AS
SELECT 
    id,
    name,
    price,
    category,
    description,
    image_url,
    sort_order
FROM menu_items
WHERE available = 1
ORDER BY sort_order, name;

-- ============================================================================
-- Завершення міграції
-- ============================================================================