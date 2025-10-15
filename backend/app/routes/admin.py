from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Product, Order, Category
from app.utils.security import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def dashboard():
    try:
        # Get dashboard statistics
        total_users = User.query.count()
        total_products = Product.query.count()
        total_orders = Order.query.count()
        total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.payment_status == 'paid'
        ).scalar() or 0
        
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        
        return jsonify({
            'stats': {
                'total_users': total_users,
                'total_products': total_products,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue)
            },
            'recent_orders': [order_to_dict(order) for order in recent_orders]
        })
        
    except Exception as e:
        current_app.logger.error(f"Admin dashboard error: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard'}), 500

@admin_bp.route('/products', methods=['POST'])
@jwt_required()
@admin_required
def create_product():
    try:
        data = request.get_json()
        
        product = Product(
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            quantity=data.get('quantity', 0),
            category_id=data.get('category_id'),
            sku=data.get('sku'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product': product_to_dict(product)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Product creation error: {str(e)}")
        return jsonify({'error': 'Failed to create product'}), 500

def product_to_dict(product):
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': float(product.price),
        'quantity': product.quantity,
        'category_id': product.category_id,
        'is_active': product.is_active,
        'created_at': product.created_at.isoformat()
    }

def order_to_dict(order):
    return {
        'id': order.id,
        'order_number': order.order_number,
        'user_id': order.user_id,
        'status': order.status,
        'total_amount': float(order.total_amount),
        'payment_status': order.payment_status,
        'created_at': order.created_at.isoformat()
    }