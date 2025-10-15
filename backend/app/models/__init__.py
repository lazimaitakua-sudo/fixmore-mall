from app import db
from datetime import datetime
import uuid
import json

def generate_uuid():
    return str(uuid.uuid4())

class BaseModel(db.Model):
    __abstract__ = True
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class User(BaseModel):
    __tablename__ = 'users'
    
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    carts = db.relationship('Cart', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True)
    addresses = db.relationship('Address', backref='user', lazy=True, cascade='all, delete-orphan')

class Address(BaseModel):
    __tablename__ = 'addresses'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    label = db.Column(db.String(50))  # Home, Work, etc.
    recipient_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='Kenya')
    is_default = db.Column(db.Boolean, default=False)

class Category(BaseModel):
    __tablename__ = 'categories'
    
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)

class Product(BaseModel):
    __tablename__ = 'products'
    
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(500))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    compare_price = db.Column(db.Numeric(10, 2))
    cost_price = db.Column(db.Numeric(10, 2))
    sku = db.Column(db.String(100), unique=True)
    barcode = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=5)
    category_id = db.Column(db.String(36), db.ForeignKey('categories.id'))
    brand = db.Column(db.String(100))
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    tags = db.Column(db.JSON)
    images = db.Column(db.JSON)
    specifications = db.Column(db.JSON)
    weight = db.Column(db.Numeric(8, 2))  # in grams
    dimensions = db.Column(db.JSON)  # {length, width, height}
    
    # Relationships
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    reviews = db.relationship('Review', backref='product', lazy=True)

class Review(BaseModel):
    __tablename__ = 'reviews'
    
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(200))
    comment = db.Column(db.Text)
    is_verified = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref='reviews', lazy=True)

class Cart(BaseModel):
    __tablename__ = 'carts'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100))
    
    # Relationships
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')

class CartItem(BaseModel):
    __tablename__ = 'cart_items'
    
    cart_id = db.Column(db.String(36), db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Numeric(10, 2), nullable=False)

class Order(BaseModel):
    __tablename__ = 'orders'
    
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, processing, shipped, delivered, cancelled
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='KES')
    shipping_address = db.Column(db.JSON)
    billing_address = db.Column(db.JSON)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(50), default='pending')  # pending, paid, failed, refunded
    payment_id = db.Column(db.String(255))
    shipping_method = db.Column(db.String(100))
    tracking_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    estimated_delivery = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy=True)

class OrderItem(BaseModel):
    __tablename__ = 'order_items'
    
    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    product_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

class Payment(BaseModel):
    __tablename__ = 'payments'
    
    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='KES')
    status = db.Column(db.String(50), default='pending')
    gateway_transaction_id = db.Column(db.String(255))
    gateway_response = db.Column(db.JSON)
    failure_reason = db.Column(db.Text)

class Inventory(BaseModel):
    __tablename__ = 'inventory'
    
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    change_quantity = db.Column(db.Integer, nullable=False)  # Positive for addition, negative for deduction
    new_quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100))  # purchase, return, adjustment, etc.
    reference_id = db.Column(db.String(36))  # order_id, etc.
    
    product = db.relationship('Product', backref='inventory_changes', lazy=True)