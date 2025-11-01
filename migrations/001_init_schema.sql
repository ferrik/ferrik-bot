-- ============================================================================
-- 🗄️ Ferrik Bot - Database Schema
-- PostgreSQL Migration Script
-- Version: 1.0
-- ============================================================================

-- Видалити існуючі таблиці (якщо потрібно)
-- DROP TABLE IF EXISTS user_profiles CASCADE;
-- DROP TABLE IF EXISTS orders CASCADE;
-- DROP TABLE IF EXISTS user_carts CASCADE;
-- DROP TABLE IF EXISTS user_states CASCADE;

-- ============================================================================
-- 1. USER STATES - Стани користувачів
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_states (
    user_id BIGINT PRIMARY KEY,
    state VARCHAR(50) DEFAULT 'idle' NOT NULL,
    state_data JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_states_state ON user_states(state);
CREATE INDEX idx_user_states_updated ON user_states(updated_at);

COMMENT ON TABLE user_states IS 'Стани користувачів в діалозі з ботом';
COMMENT ON COLUMN user_states.state IS 'Поточний стан: idle, awaiting_phone, awaiting_address, etc.';
COMMENT ON COLUMN user_states.state_data IS 'Додаткові дані стану (JSON)';

-- ============================================================================
-- 2. USER CARTS - Кошики покупок
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_carts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    item_id VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    quantity INTEGER DEFAULT 1 CHECK (quantity > 0),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_carts_user_id ON user_carts(user_id);
CREATE INDEX idx_user_carts_item_id ON user_carts(item_id);
CREATE INDEX idx_user_carts_updated ON user_carts(updated_at);
CREATE UNIQUE INDEX idx_user_carts_user_item ON user_carts(user_id, item_id);

COMMENT ON TABLE user_carts IS 'Кошики покупок користувачів';
COMMENT ON COLUMN user_carts.item_id IS 'ID товару з Google Sheets';
COMMENT ON COLUMN user_carts.price IS 'Ціна товару на момент додавання';
COMMENT ON COLUMN user_carts.quantity IS 'Кількість товару';

-- ============================================================================
-- 3. ORDERS - Історія замовлень
-- ============================================================================
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    items_json JSONB NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_order_number ON orders(order_number);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

COMMENT ON TABLE orders IS 'Історія замовлень';
COMMENT ON COLUMN orders.order_number IS 'Унікальний номер замовлення (F20251031...)';
COMMENT ON COLUMN orders.items_json IS 'JSON з товарами замовлення';
COMMENT ON COLUMN orders.status IS 'Статус: pending, confirmed, delivered, cancelled';

-- ============================================================================
-- 4. USER PROFILES - Профілі для геймифікації
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(100),
    first_name VARCHAR(100),
    total_orders INTEGER DEFAULT 0 CHECK (total_orders >= 0),
    total_spent DECIMAL(10, 2) DEFAULT 0.00 CHECK (total_spent >= 0),
    level VARCHAR(50) DEFAULT 'Новачок',
    badges JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_profiles_level ON user_profiles(level);
CREATE INDEX idx_user_profiles_total_orders ON user_profiles(total_orders DESC);
CREATE INDEX idx_user_profiles_total_spent ON user_profiles(total_spent DESC);

COMMENT ON TABLE user_profiles IS 'Профілі користувачів з статистикою';
COMMENT ON COLUMN user_profiles.level IS 'Рівень користувача: Новачок, Любитель, Гурман, Майстер, Легенда';
COMMENT ON COLUMN user_profiles.badges IS 'JSON масив з отриманими бейджами';

-- ============================================================================
-- 5. TRIGGERS - Автоматичне оновлення timestamps
-- ============================================================================

-- Функція для оновлення updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Тригери для автооновлення
DROP TRIGGER IF EXISTS update_user_states_updated_at ON user_states;
CREATE TRIGGER update_user_states_updated_at
    BEFORE UPDATE ON user_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_carts_updated_at ON user_carts;
CREATE TRIGGER update_user_carts_updated_at
    BEFORE UPDATE ON user_carts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. VIEWS - Корисні представлення
-- ============================================================================

-- Активні користувачі (зробили хоча б 1 замовлення)
CREATE OR REPLACE VIEW active_users AS
SELECT 
    up.*,
    COUNT(o.id) as order_count,
    MAX(o.created_at) as last_order_date
FROM user_profiles up
LEFT JOIN orders o ON up.user_id = o.user_id
GROUP BY up.user_id
HAVING COUNT(o.id) > 0;

COMMENT ON VIEW active_users IS 'Користувачі з хоча б одним замовленням';

-- Популярні товари
CREATE OR REPLACE VIEW popular_items AS
SELECT 
    item->>'name' as item_name,
    item->>'item_id' as item_id,
    COUNT(*) as order_count,
    SUM((item->>'quantity')::integer) as total_quantity,
    AVG((item->>'price')::decimal) as avg_price
FROM orders,
     jsonb_array_elements(items_json) as item
GROUP BY item->>'name', item->>'item_id'
ORDER BY order_count DESC;

COMMENT ON VIEW popular_items IS 'Топ популярних товарів';

-- Статистика по днях
CREATE OR REPLACE VIEW daily_stats AS
SELECT 
    DATE(created_at) as order_date,
    COUNT(*) as total_orders,
    SUM(total_amount) as total_revenue,
    AVG(total_amount) as avg_order_value,
    COUNT(DISTINCT user_id) as unique_customers
FROM orders
GROUP BY DATE(created_at)
ORDER BY order_date DESC;

COMMENT ON VIEW daily_stats IS 'Денна статистика замовлень';

-- ============================================================================
-- 7. SAMPLE DATA (для тестування)
-- ============================================================================

-- Тестовий користувач
INSERT INTO user_profiles (user_id, username, first_name, level)
VALUES (123456789, 'test_user', 'Тестовий', 'Новачок')
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================================
-- 8. GRANTS (якщо потрібно)
-- ============================================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ferrik_bot_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ferrik_bot_user;

-- ============================================================================
-- 9. MAINTENANCE QUERIES (для адміністрування)
-- ============================================================================

-- Очистка старих кошиків (>7 днів)
-- DELETE FROM user_carts WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '7 days';

-- Архівація старих замовлень (>1 рік)
-- CREATE TABLE orders_archive AS SELECT * FROM orders WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 year';
-- DELETE FROM orders WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 year';

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$ 
BEGIN 
    RAISE NOTICE '✅ Database schema initialized successfully!';
    RAISE NOTICE '📊 Tables created: user_states, user_carts, orders, user_profiles';
    RAISE NOTICE '🔍 Views created: active_users, popular_items, daily_stats';
    RAISE NOTICE '⚡ Triggers enabled for auto-updating timestamps';
END $$;
