-- ============================================================================
-- Ferrik Bot 2.0 - Повна схема бази даних
-- ============================================================================

-- Користувачі
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    address TEXT,
    
    -- Гейміфікація
    total_xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    bonus_points INTEGER DEFAULT 0,
    
    -- Реферальна програма
    referral_code TEXT UNIQUE,
    referred_by INTEGER,  -- ID користувача, що запросив
    
    -- Статистика
    total_orders INTEGER DEFAULT 0,
    total_spent REAL DEFAULT 0.0,
    
    -- Налаштування
    notifications_enabled BOOLEAN DEFAULT 1,
    language TEXT DEFAULT 'uk',
    
    -- Метадані
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (referred_by) REFERENCES users(telegram_user_id)
);

-- Індекси для users
CREATE INDEX idx_users_telegram_id ON users(telegram_user_id);
CREATE INDEX idx_users_referral_code ON users(referral_code);


-- ============================================================================
-- Стани користувачів
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_states (
    user_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'idle',
    state_data TEXT,  -- JSON з додатковими даними
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id)
);


-- ============================================================================
-- Кошики
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_carts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    category TEXT,
    quantity INTEGER DEFAULT 1,
    price REAL NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id),
    UNIQUE(user_id, item_id)
);

CREATE INDEX idx_carts_user_id ON user_carts(user_id);


-- ============================================================================
-- Замовлення
-- ============================================================================
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    
    -- Контактна інформація
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    
    -- Дані замовлення
    items_json TEXT NOT NULL,  -- JSON з товарами
    total_amount REAL NOT NULL,
    delivery_cost REAL DEFAULT 0.0,
    discount_amount REAL DEFAULT 0.0,
    final_amount REAL NOT NULL,
    
    -- Статус
    status TEXT DEFAULT 'new',
    payment_method TEXT DEFAULT 'cash',
    payment_status TEXT DEFAULT 'pending',
    
    -- Доставка
    estimated_delivery_time INTEGER,  -- хвилини
    actual_delivery_time INTEGER,
    courier_id INTEGER,
    
    -- Промокод
    promo_code TEXT,
    promo_discount REAL DEFAULT 0.0,
    
    -- Метадані
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    
    -- Відгук
    rating INTEGER,
    review_text TEXT,
    reviewed_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id)
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);


-- ============================================================================
-- Історія статусів замовлень
-- ============================================================================
CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    comment TEXT,
    changed_by TEXT,  -- system/admin/user
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE INDEX idx_status_history_order_id ON order_status_history(order_id);


-- ============================================================================
-- Бейджі та досягнення
-- ============================================================================
CREATE TABLE IF NOT EXISTS badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    badge_type TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    emoji TEXT,
    xp_reward INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Попередньо заповнюємо бейджі
INSERT OR IGNORE INTO badges (badge_type, name, description, emoji, xp_reward) VALUES
    ('explorer', 'Дослідник смаку', 'Переглянув меню вперше', '🔍', 10),
    ('first_order', 'Перше замовлення', 'Зробив перше замовлення', '🎉', 50),
    ('shopper', 'Покупець', 'Додав товар у кошик', '🛒', 20),
    ('regular', 'Постійний клієнт', '10 замовлень', '⭐', 100),
    ('foodie', 'Фуді', '25 замовлень', '🍽️', 250),
    ('gourmet', 'Гурман', '50 замовлень', '👨‍🍳', 500),
    ('legend', 'Легенда', '100 замовлень', '🏆', 1000),
    ('pizza_lover', 'Любитель піци', 'Замовив 10 піц', '🍕', 150),
    ('sweet_tooth', 'Ласунчик', 'Замовив 10 десертів', '🍰', 150),
    ('healthy', 'Здоровий стиль', 'Замовив 10 салатів', '🥗', 150),
    ('night_owl', 'Нічна сова', '5 замовлень після 22:00', '🦉', 75),
    ('early_bird', 'Рання пташка', '5 замовлень до 9:00', '🐦', 75),
    ('referrer', 'Друг друзів', 'Запросив 3 друзів', '🤝', 200),
    ('influencer', 'Інфлюенсер', 'Запросив 10 друзів', '📱', 500),
    ('reviewer', 'Рецензент', 'Залишив 5 відгуків', '📝', 100),
    ('critic', 'Критик', 'Залишив 20 відгуків', '🎭', 300);


-- Бейджі користувачів
CREATE TABLE IF NOT EXISTS user_badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    badge_type TEXT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id),
    FOREIGN KEY (badge_type) REFERENCES badges(badge_type),
    UNIQUE(user_id, badge_type)
);

CREATE INDEX idx_user_badges_user_id ON user_badges(user_id);


-- ============================================================================
-- Історія досвіду (XP)
-- ============================================================================
CREATE TABLE IF NOT EXISTS xp_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,  -- order/badge/referral/review
    reference_id INTEGER,  -- ID замовлення, бейджа тощо
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id)
);

CREATE INDEX idx_xp_history_user_id ON xp_history(user_id);


-- ============================================================================
-- Квести та челенджі
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_quest_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    quest_type TEXT NOT NULL,  -- onboarding/weekly/special
    quest_stage INTEGER DEFAULT 0,
    quest_data TEXT,  -- JSON з прогресом
    completed BOOLEAN DEFAULT 0,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id)
);

CREATE INDEX idx_quest_user_id ON user_quest_progress(user_id);


-- ============================================================================
-- Реферали
-- ============================================================================
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,  -- Хто запросив
    referee_id INTEGER NOT NULL,   -- Кого запросив
    referral_code TEXT NOT NULL,
    
    -- Винагороди
    referrer_bonus_given BOOLEAN DEFAULT 0,
    referee_bonus_given BOOLEAN DEFAULT 0,
    
    -- Статистика
    referee_first_order_at TIMESTAMP,
    total_referee_orders INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (referrer_id) REFERENCES users(telegram_user_id),
    FOREIGN KEY (referee_id) REFERENCES users(telegram_user_id),
    UNIQUE(referee_id)  -- Користувач може бути запрошений тільки один раз
);

CREATE INDEX idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX idx_referrals_referee_id ON referrals(referee_id);


-- ============================================================================
-- Промокоди
-- ============================================================================
CREATE TABLE IF NOT EXISTS promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    discount_type TEXT NOT NULL,  -- percent/fixed
    discount_value REAL NOT NULL,
    
    -- Обмеження
    min_order_amount REAL DEFAULT 0.0,
    max_uses INTEGER,
    max_uses_per_user INTEGER DEFAULT 1,
    
    -- Період дії
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,
    
    -- Статистика
    times_used INTEGER DEFAULT 0,
    
    -- Спеціальні
    user_specific INTEGER,  -- Для конкретного користувача
    first_order_only BOOLEAN DEFAULT 0,
    
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_specific) REFERENCES users(telegram_user_id)
);

CREATE INDEX idx_promo_codes_code ON promo_codes(code);
CREATE INDEX idx_promo_codes_active ON promo_codes(active);


-- Історія використання промокодів
CREATE TABLE IF NOT EXISTS promo_code_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_code_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    discount_applied REAL NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id),
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE INDEX idx_promo_usage_user_id ON promo_code_usage(user_id);


-- ============================================================================
-- Відгуки
-- ============================================================================
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    
    -- Оцінки
    overall_rating INTEGER NOT NULL,  -- 1-5
    food_quality INTEGER,  -- 1-5
    delivery_speed INTEGER,  -- 1-5
    service_quality INTEGER,  -- 1-5
    
    -- Текстовий відгук
    comment TEXT,
    
    -- Модерація
    approved BOOLEAN DEFAULT 0,
    moderated_at TIMESTAMP,
    
    -- Реакції
    helpful_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    UNIQUE(user_id, order_id)
);

CREATE INDEX idx_reviews_user_id ON reviews(user_id);
CREATE INDEX idx_reviews_order_id ON reviews(order_id);


-- ============================================================================
-- Улюблені товари
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    category TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id),
    UNIQUE(user_id, item_id)
);

CREATE INDEX idx_favorites_user_id ON user_favorites(user_id);


-- ============================================================================
-- Історія активності
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- view_menu/add_cart/search/etc
    action_data TEXT,  -- JSON з деталями
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id)
);

CREATE INDEX idx_activity_user_id ON user_activity_log(user_id);
CREATE INDEX idx_activity_created_at ON user_activity_log(created_at);


-- ============================================================================
-- Кеш меню
-- ============================================================================
CREATE TABLE IF NOT EXISTS menu_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    cache_data TEXT NOT NULL,  -- JSON
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_menu_cache_key ON menu_cache(cache_key);
CREATE INDEX idx_menu_cache_expires ON menu_cache(expires_at);


-- ============================================================================
-- Сповіщення (черга)
-- ============================================================================
CREATE TABLE IF NOT EXISTS notification_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message_type TEXT NOT NULL,  -- order_status/promo/reminder
    message_text TEXT NOT NULL,
    message_data TEXT,  -- JSON
    
    -- Статус
    sent BOOLEAN DEFAULT 0,
    sent_at TIMESTAMP,
    failed BOOLEAN DEFAULT 0,
    error_message TEXT,
    
    -- Планування
    scheduled_for TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id)
);

CREATE INDEX idx_notifications_user_id ON notification_queue(user_id);
CREATE INDEX idx_notifications_sent ON notification_queue(sent);
CREATE INDEX idx_notifications_scheduled ON notification_queue(scheduled_for);


-- ============================================================================
-- Адмін-лог
-- ============================================================================
CREATE TABLE IF NOT EXISTS admin_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT,  -- order/user/promo
    entity_id INTEGER,
    details TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (admin_user_id) REFERENCES users(telegram_user_id)
);

CREATE INDEX idx_admin_log_created_at ON admin_log(created_at);


-- ============================================================================
-- Тригери для автоматичного оновлення updated_at
-- ============================================================================
CREATE TRIGGER update_users_timestamp 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_orders_timestamp 
AFTER UPDATE ON orders
BEGIN
    UPDATE orders SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;


-- ============================================================================
-- В'юшки для статистики
-- ============================================================================

-- Топ користувачів за замовленнями
CREATE VIEW IF NOT EXISTS top_users AS
SELECT 
    u.telegram_user_id,
    u.first_name,
    u.total_orders,
    u.total_spent,
    u.level,
    COUNT(ub.id) as badges_count
FROM users u
LEFT JOIN user_badges ub ON u.telegram_user_id = ub.user_id
GROUP BY u.telegram_user_id
ORDER BY u.total_orders DESC
LIMIT 100;


-- Статистика замовлень по днях
CREATE VIEW IF NOT EXISTS orders_daily_stats AS
SELECT 
    DATE(created_at) as order_date,
    COUNT(*) as total_orders,
    SUM(final_amount) as total_revenue,
    AVG(final_amount) as avg_order_value,
    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered_count,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_count
FROM orders
GROUP BY DATE(created_at)
ORDER BY order_date DESC;


-- Популярні товари
CREATE VIEW IF NOT EXISTS popular_items AS
SELECT 
    item_name,
    category,
    COUNT(*) as order_count,
    SUM(quantity) as total_quantity,
    AVG(price) as avg_price
FROM (
    SELECT 
        json_extract(value, '$.name') as item_name,
        json_extract(value, '$.category') as category,
        json_extract(value, '$.quantity') as quantity,
        json_extract(value, '$.price') as price
    FROM orders, json_each(orders.items_json)
    WHERE status = 'delivered'
)
GROUP BY item_name
ORDER BY order_count DESC
LIMIT 50;
