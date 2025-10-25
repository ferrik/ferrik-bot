-- ============================================================================
-- Міграція 001: Створення базових таблиць
-- ============================================================================
-- Дата: 2025-10-24
-- Опис: Створення таблиць для станів користувачів, кошиків та інше
-- ============================================================================

-- Таблиця станів користувачів
CREATE TABLE IF NOT EXISTS user_states (
    user_id INTEGER PRIMARY KEY,
    state TEXT DEFAULT 'STATE_IDLE' NOT NULL,
    state_data TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Індекс для швидкого пошуку по стану
CREATE INDEX IF NOT EXISTS idx_user_states_state ON user_states(state);

-- Таблиця кошиків
CREATE TABLE IF NOT EXISTS user_carts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 1 NOT NULL CHECK(quantity > 0),
    price REAL DEFAULT 0 NOT NULL CHECK(price >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_id)
);

-- Індекси для кошиків
CREATE INDEX IF NOT EXISTS idx_carts_user ON user_carts(user_id);
CREATE INDEX IF NOT EXISTS idx_carts_item ON user_carts(item_id);

-- Таблиця замовлень (якщо використовуєте SQLite замість Sheets)
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    items_json TEXT NOT NULL,  -- JSON масив товарів
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'in_progress', 'delivered', 'cancelled')),
    partner_id INTEGER,
    commission_amount REAL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Індекси для замовлень
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);

-- Таблиця відгуків
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    order_id INTEGER,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Індекси для відгуків
CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order ON reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);

-- Таблиця кешу (для меню та інших даних)
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Індекс для швидкого очищення застарілого кешу
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);

-- Таблиця логів (опціонально - для аудиту)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Індекс для логів
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

-- Таблиця обробки webhook (захист від дублікатів)
CREATE TABLE IF NOT EXISTS processed_updates (
    update_id INTEGER PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Індекс для автоочищення старих записів
CREATE INDEX IF NOT EXISTS idx_updates_processed ON processed_updates(processed_at);

-- ============================================================================
-- Тригери для автоматичного оновлення updated_at
-- ============================================================================

-- Тригер для user_states
CREATE TRIGGER IF NOT EXISTS update_user_states_timestamp 
AFTER UPDATE ON user_states
BEGIN
    UPDATE user_states SET updated_at = CURRENT_TIMESTAMP 
    WHERE user_id = NEW.user_id;
END;

-- Тригер для user_carts
CREATE TRIGGER IF NOT EXISTS update_user_carts_timestamp 
AFTER UPDATE ON user_carts
BEGIN
    UPDATE user_carts SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Тригер для orders
CREATE TRIGGER IF NOT EXISTS update_orders_timestamp 
AFTER UPDATE ON orders
BEGIN
    UPDATE orders SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- ============================================================================
-- Views для зручності
-- ============================================================================

-- View: Активні кошики з підрахунком
CREATE VIEW IF NOT EXISTS active_carts AS
SELECT 
    user_id,
    COUNT(*) as items_count,
    SUM(quantity) as total_quantity,
    SUM(quantity * price) as total_amount
FROM user_carts
GROUP BY user_id;

-- View: Статистика замовлень
CREATE VIEW IF NOT EXISTS order_stats AS
SELECT 
    user_id,
    COUNT(*) as total_orders,
    SUM(total_amount) as total_spent,
    AVG(total_amount) as avg_order,
    MAX(created_at) as last_order
FROM orders
WHERE status != 'cancelled'
GROUP BY user_id;

-- View: Середній рейтинг
CREATE VIEW IF NOT EXISTS average_ratings AS
SELECT 
    order_id,
    AVG(rating) as avg_rating,
    COUNT(*) as review_count
FROM reviews
GROUP BY order_id;

-- ============================================================================
-- Початкові дані (опціонально)
-- ============================================================================

-- Додати системного користувача для тестів
INSERT OR IGNORE INTO user_states (user_id, state, state_data)
VALUES (0, 'STATE_IDLE', '{"is_test": true}');

-- ============================================================================
-- Очищення старих даних (функція для запуску вручну)
-- ============================================================================

-- Видалити оброблені update старші 24 годин
-- DELETE FROM processed_updates WHERE processed_at < datetime('now', '-1 day');

-- Видалити застарілий кеш
-- DELETE FROM cache WHERE expires_at < CURRENT_TIMESTAMP;

-- Очистити старі логи (старші 30 днів)
-- DELETE FROM audit_log WHERE created_at < datetime('now', '-30 days');

-- ============================================================================
-- Перевірка цілісності
-- ============================================================================

-- Перевірити що всі таблиці створені
SELECT 
    name, 
    type,
    sql IS NOT NULL as has_definition
FROM sqlite_master 
WHERE type IN ('table', 'view', 'trigger', 'index')
ORDER BY type, name;

-- ============================================================================
-- Завершення міграції
-- ============================================================================

-- Якщо всі команди виконалися успішно, міграція завершена!
