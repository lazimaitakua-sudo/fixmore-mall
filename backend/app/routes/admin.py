from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Product, Order, Category, Payment, Review
from app.utils.security import admin_required
from sqlalchemy import func, desc
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def dashboard():
    try:
        # Basic statistics
        total_users = User.query.count()
        total_products = Product.query.count()
        total_orders = Order.query.count()
        total_revenue = db.session.query(
            func.sum(Order.total_amount)
        ).filter(Order.payment_status == 'paid').scalar() or 0
        
        # Recent orders
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        
        # Sales data for chart (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        sales_data = db.session.query(
            func.date(Order.created_at).label('date'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders')
        ).filter(
            Order.created_at >= thirty_days_ago,
            Order.payment_status == 'paid'
        ).group_by(
            func.date(Order.created_at)
        ).order_by('date').all()
        
        # Low stock products
        low_stock_products = Product.query.filter(
            Product.quantity <= Product.low_stock_threshold
        ).limit(5).all()
        
        # Payment methods breakdown
        payment_methods = db.session.query(
            Payment.payment_method,
            func.count(Payment.id).label('count'),
            func.sum(Payment.amount).label('amount')
        ).filter(Payment.status == 'paid').group_by(Payment.payment_method).all()
        
        return jsonify({
            'stats': {
                'total_users': total_users,
                'total_products': total_products,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'active_orders': Order.query.filter(Order.status.in_(['pending', 'confirmed', 'processing'])).count()
            },
            'sales_data': [{
                'date': row.date.isoformat(),
                'revenue': float(row.revenue or 0),
                'orders': row.orders
            } for row in sales_data],
            'recent_orders': [order_to_dict(order) for order in recent_orders],
            'low_stock_products': [product_to_dict(product) for product in low_stock_products],
            'payment_methods': [{
                'method': row.payment_method,
                'count': row.count,
                'amount': float(row.amount or 0)
            } for row in payment_methods]
        })
        
    except Exception as e:
        current_app.logger.error(f"Admin dashboard error: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard'}), 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_users():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search')
        
        query = User.query
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term))
            )
        
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user_to_dict(user) for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        })
        
    except Exception as e:
        current_app.logger.error(f"Get users error: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@admin_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = user_to_dict(user)
        user_data['orders_count'] = len(user.orders)
        user_data['total_spent'] = float(sum(order.total_amount for order in user.orders if order.payment_status == 'paid'))
        
        return jsonify({'user': user_data})
        
    except Exception as e:
        current_app.logger.error(f"Get user error: {str(e)}")
        return jsonify({'error': 'Failed to fetch user'}), 500

@admin_bp.route('/products', methods=['GET'])
@jwt_required()
@admin_required
def get_products_admin():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category')
        low_stock = request.args.get('low_stock', type=bool)
        
        query = Product.query
        
        if category:
            query = query.filter(Product.category.has(name=category))
        
        if low_stock:
            query = query.filter(Product.quantity <= Product.low_stock_threshold)
        
        products = query.order_by(Product.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'products': [product_to_dict(product) for product in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        })
        
    except Exception as e:
        current_app.logger.error(f"Get products admin error: {str(e)}")
        return jsonify({'error': 'Failed to fetch products'}), 500

@admin_bp.route('/products', methods=['POST'])
@jwt_required()
@admin_required
def create_product():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'price', 'category_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if SKU is unique
        if data.get('sku'):
            existing_product = Product.query.filter_by(sku=data['sku']).first()
            if existing_product:
                return jsonify({'error': 'SKU already exists'}), 400
        
        product = Product(
            name=data['name'],
            description=data.get('description'),
            short_description=data.get('short_description'),
            price=data['price'],
            compare_price=data.get('compare_price'),
            cost_price=data.get('cost_price'),
            sku=data.get('sku'),
            barcode=data.get('barcode'),
            quantity=data.get('quantity', 0),
            low_stock_threshold=data.get('low_stock_threshold', 5),
            category_id=data['category_id'],
            brand=data.get('brand'),
            is_featured=data.get('is_featured', False),
            is_active=data.get('is_active', True),
            tags=data.get('tags', []),
            images=data.get('images', []),
            specifications=data.get('specifications', {}),
            weight=data.get('weight'),
            dimensions=data.get('dimensions')
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product': product_to_dict(product)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create product error: {str(e)}")
        return jsonify({'error': 'Failed to create product'}), 500

@admin_bp.route('/products/<product_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        data = request.get_json()
        
        # Update fields
        updatable_fields = [
            'name', 'description', 'short_description', 'price', 'compare_price',
            'cost_price', 'quantity', 'low_stock_threshold', 'category_id',
            'brand', 'is_featured', 'is_active', 'tags', 'images',
            'specifications', 'weight', 'dimensions'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(product, field, data[field])
        
        # Handle SKU uniqueness
        if data.get('sku') and data['sku'] != product.sku:
            existing_product = Product.query.filter_by(sku=data['sku']).first()
            if existing_product:
                return jsonify({'error': 'SKU already exists'}), 400
            product.sku = data['sku']
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Product updated successfully',
            'product': product_to_dict(product)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update product error: {str(e)}")
        return jsonify({'error': 'Failed to update product'}), 500

@admin_bp.route('/products/<product_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if product has orders
        if product.order_items:
            return jsonify({'error': 'Cannot delete product with existing orders'}), 400
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'message': 'Product deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete product error: {str(e)}")
        return jsonify({'error': 'Failed to delete product'}), 500

@admin_bp.route('/orders', methods=['GET'])
@jwt_required()
@admin_required
def get_orders_admin():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        payment_status = request.args.get('payment_status')
        
        query = Order.query
        
        if status:
            query = query.filter_by(status=status)
        if payment_status:
            query = query.filter_by(payment_status=payment_status)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order_to_dict(order, include_user=True) for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page
        })
        
    except Exception as e:
        current_app.logger.error(f"Get orders admin error: {str(e)}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@admin_bp.route('/orders/<order_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_order(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        data = request.get_json()
        
        # Update status
        if 'status' in data:
            valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
            if data['status'] in valid_statuses:
                order.status = data['status']
        
        # Update tracking info
        if 'tracking_number' in data:
            order.tracking_number = data['tracking_number']
        
        if 'shipping_method' in data:
            order.shipping_method = data['shipping_method']
        
        if 'estimated_delivery' in data:
            order.estimated_delivery = datetime.fromisoformat(data['estimated_delivery'])
        
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Order updated successfully',
            'order': order_to_dict(order, include_user=True)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update order error: {str(e)}")
        return jsonify({'error': 'Failed to update order'}), 500

@admin_bp.route('/categories', methods=['GET'])
@jwt_required()
@admin_required
def get_categories_admin():
    try:
        categories = Category.query.order_by(Category.sort_order, Category.name).all()
        return jsonify([category_to_dict(category) for category in categories])
        
    except Exception as e:
        current_app.logger.error(f"Get categories admin error: {str(e)}")
        return jsonify({'error': 'Failed to fetch categories'}), 500

@admin_bp.route('/categories', methods=['POST'])
@jwt_required()
@admin_required
def create_category():
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Category name is required'}), 400
        
        # Check if category already exists
        existing_category = Category.query.filter_by(name=data['name']).first()
        if existing_category:
            return jsonify({'error': 'Category already exists'}), 400
        
        category = Category(
            name=data['name'],
            description=data.get('description'),
            image_url=data.get('image_url'),
            is_active=data.get('is_active', True),
            sort_order=data.get('sort_order', 0)
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Category created successfully',
            'category': category_to_dict(category)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create category error: {str(e)}")
        return jsonify({'error': 'Failed to create category'}), 500

# Helper functions
def user_to_dict(user):
    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': user.phone,
        'is_active': user.is_active,
        'is_admin': user.is_admin,
        'email_verified': user.email_verified,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'created_at': user.created_at.isoformat()
    }

def product_to_dict(product):
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': float(product.price),
        'compare_price': float(product.compare_price) if product.compare_price else None,
        'cost_price': float(product.cost_price) if product.cost_price else None,
        'quantity': product.quantity,
        'low_stock_threshold': product.low_stock_threshold,
        'category_id': product.category_id,
        'brand': product.brand,
        'is_featured': product.is_featured,
        'is_active': product.is_active,
        'sku': product.sku,
        'barcode': product.barcode,
        'tags': product.tags or [],
        'images': product.images or [],
        'specifications': product.specifications or {},
        'created_at': product.created_at.isoformat(),
        'updated_at': product.updated_at.isoformat()
    }

def order_to_dict(order, include_user=False, include_items=False):
    data = {
        'id': order.id,
        'order_number': order.order_number,
        'status': order.status,
        'subtotal': float(order.subtotal),
        'tax_amount': float(order.tax_amount),
        'shipping_amount': float(order.shipping_amount),
        'total_amount': float(order.total_amount),
        'payment_method': order.payment_method,
        'payment_status': order.payment_status,
        'shipping_address': order.shipping_address,
        'tracking_number': order.tracking_number,
        'shipping_method': order.shipping_method,
        'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        'created_at': order.created_at.isoformat()
    }
    
    if include_user:
        data['user'] = {
            'id': order.user.id,
            'email': order.user.email,
            'first_name': order.user.first_name,
            'last_name': order.user.last_name,
            'phone': order.user.phone
        }
    
    if include_items:
        data['items'] = [{
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product_name,
            'quantity': item.quantity,
            'price': float(item.product_price),
            'total': float(item.total_price)
        } for item in order.items]
    
    return data

def category_to_dict(category):
    return {
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'image_url': category.image_url,
        'is_active': category.is_active,
        'sort_order': category.sort_order,
        'product_count': len(category.products),
        'created_at': category.created_at.isoformat()
    }