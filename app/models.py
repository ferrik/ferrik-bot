# Тільки змінити ці частини:

# ============================================================================
# 4. ЗАМОВЛЕННЯ (Order) - ФІКСОВАНО
# ============================================================================

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)  # ← INTEGER (основний ключ)
    external_id = Column(String(100), unique=True, nullable=False)
    telegram_user_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    total_amount = Column(Float, nullable=False)
    delivery_cost = Column(Float, default=30.0)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=False)
    payment_method = Column(String(50), default='cash')
    status = Column(String(50), default='new')
    promo_code = Column(String(50))
    commission_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship('User', back_populates='orders')
    restaurant = relationship('Restaurant', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    review = relationship('Review', uselist=False, back_populates='order')
    
    __table_args__ = (
        Index('idx_order_user', 'telegram_user_id'),
        Index('idx_order_restaurant', 'restaurant_id'),
        Index('idx_order_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Order {self.external_id} - {self.status}>"


# ============================================================================
# 5. ТОВАР У ЗАМОВЛЕННІ (OrderItem) - ФІКСОВАНО
# ============================================================================

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)  # ← INTEGER (посилається на Order.id)
    menu_item_id = Column(Integer, ForeignKey('menu_items.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relationship
    order = relationship('Order', back_populates='items')
    menu_item = relationship('MenuItem', back_populates='order_items')
    
    def __repr__(self):
        return f"<OrderItem {self.menu_item} x{self.quantity}>"


# ============================================================================
# 7. ВІДГУК (Review) - ФІКСОВАНО
# ============================================================================

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)  # ← INTEGER (посилається на Order.id)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    telegram_user_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    order = relationship('Order', back_populates='review')
    restaurant = relationship('Restaurant', back_populates='reviews')
    user = relationship('User', back_populates='reviews')
    
    __table_args__ = (
        Index('idx_review_restaurant', 'restaurant_id'),
    )
    
    def __repr__(self):
        return f"<Review {self.restaurant.name} - {self.rating}⭐>"
