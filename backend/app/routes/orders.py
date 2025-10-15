from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Order, OrderItem, Cart, CartItem, Product, User, Payment
from app.services.payment_service import PaymentService
from datetime import datetime
import uuid

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/', methods=['GET'])
@jwt_required()
def get_orders():
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        query = Order.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order_to_dict(order) for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page
        })
        
    except Exception as e:
        current_app.logger.error(f"Get orders error: {str(e)}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@orders_bp.route('/', methods=['POST'])
@jwt_required()
def create_order():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Get user's cart
        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart or not cart.items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Calculate totals
        subtotal = sum(float(item.price) * item.quantity for item in cart.items)
        tax_amount = subtotal * 0.16  # 16% VAT for Kenya
        shipping_amount = 0 if subtotal > 5000 else 300  # Free shipping over 5000 KES
        total_amount = subtotal + tax_amount + shipping_amount
        
        # Generate order number
        order_number = f"FM{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        
        # Create order
        order = Order(
            order_number=order_number,
            user_id=user_id,
            status='pending',
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            shipping_address=data.get('shipping_address'),
            billing_address=data.get('billing_address', data.get('shipping_address')),
            payment_method=data.get('payment_method'),
            notes=data.get('notes')
        )
        
        db.session.add(order)
        
        # Create order items and update product quantities
        for cart_item in cart.items:
            product = Product.query.get(cart_item.product_id)
            if not product:
                return jsonify({'error': f'Product {cart_item.product_id} not found'}), 404
            
            if product.quantity < cart_item.quantity:
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
            
            # Reduce product quantity
            product.quantity -= cart_item.quantity
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                product_name=product.name,
                product_price=cart_item.price,
                quantity=cart_item.quantity,
                total_price=float(cart_item.price) * cart_item.quantity
            )
            db.session.add(order_item)
        
        # Clear cart
        CartItem.query.filter_by(cart_id=cart.id).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order_to_dict(order)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create order error: {str(e)}")
        return jsonify({'error': 'Failed to create order'}), 500

@orders_bp.route('/<order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    try:
        user_id = get_jwt_identity()
        order = Order.query.filter_by(id=order_id, user_id=user_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify(order_to_dict(order, include_items=True))
        
    except Exception as e:
        current_app.logger.error(f"Get order error: {str(e)}")
        return jsonify({'error': 'Failed to fetch order'}), 500

@orders_bp.route('/<order_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    try:
        user_id = get_jwt_identity()
        order = Order.query.filter_by(id=order_id, user_id=user_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        if order.status not in ['pending', 'confirmed']:
            return jsonify({'error': 'Order cannot be cancelled at this stage'}), 400
        
        # Restore product quantities
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.quantity += item.quantity
        
        order.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'message': 'Order cancelled successfully',
            'order': order_to_dict(order)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cancel order error: {str(e)}")
        return jsonify({'error': 'Failed to cancel order'}), 500

@orders_bp.route('/<order_id>/track', methods=['GET'])
@jwt_required()
def track_order(order_id):
    try:
        user_id = get_jwt_identity()
        order = Order.query.filter_by(id=order_id, user_id=user_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Mock tracking information - in real app, integrate with shipping provider
        tracking_info = {
            'order_number': order.order_number,
            'status': order.status,
            'tracking_number': order.tracking_number,
            'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
            'history': [
                {
                    'status': 'ordered',
                    'timestamp': order.created_at.isoformat(),
                    'description': 'Order placed'
                }
            ]
        }
        
        # Add status-specific updates
        if order.status in ['processing', 'shipped', 'delivered']:
            tracking_info['history'].append({
                'status': 'confirmed',
                'timestamp': (order.created_at.replace(second=0, microsecond=0)).isoformat(),
                'description': 'Order confirmed'
            })
        
        if order.status in ['shipped', 'delivered']:
            tracking_info['history'].append({
                'status': 'shipped',
                'timestamp': (order.created_at.replace(hour=12, minute=0, second=0, microsecond=0)).isoformat(),
                'description': 'Order shipped'
            })
        
        if order.status == 'delivered':
            tracking_info['history'].append({
                'status': 'delivered',
                'timestamp': (order.created_at.replace(hour=14, minute=0, second=0, microsecond=0)).isoformat(),
                'description': 'Order delivered'
            })
        
        return jsonify(tracking_info)
        
    except Exception as e:
        current_app.logger.error(f"Track order error: {str(e)}")
        return jsonify({'error': 'Failed to track order'}), 500

def order_to_dict(order, include_items=False):
    data = {
        'id': order.id,
        'order_number': order.order_number,
        'status': order.status,
        'subtotal': float(order.subtotal),
        'tax_amount': float(order.tax_amount),
        'shipping_amount': float(order.shipping_amount),
        'total_amount': float(order.total_amount),
        'currency': order.currency,
        'payment_method': order.payment_method,
        'payment_status': order.payment_status,
        'shipping_address': order.shipping_address,
        'created_at': order.created_at.isoformat(),
        'updated_at': order.updated_at.isoformat()
    }
    
    if include_items:
        data['items'] = [order_item_to_dict(item) for item in order.items]
        data['payments'] = [payment_to_dict(payment) for payment in order.payments]
    
    return data

def order_item_to_dict(item):
    return {
        'id': item.id,
        'product_id': item.product_id,
        'product_name': item.product_name,
        'product_price': float(item.product_price),
        'quantity': item.quantity,
        'total_price': float(item.total_price)
    }

def payment_to_dict(payment):
    return {
        'id': payment.id,
        'payment_method': payment.payment_method,
        'amount': float(payment.amount),
        'status': payment.status,
        'gateway_transaction_id': payment.gateway_transaction_id,
        'created_at': payment.created_at.isoformat()
    }