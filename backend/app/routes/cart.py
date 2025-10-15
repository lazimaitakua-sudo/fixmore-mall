from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Cart, CartItem, Product

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/', methods=['GET'])
@jwt_required()
def get_cart():
    try:
        user_id = get_jwt_identity()
        cart = Cart.query.filter_by(user_id=user_id).first()
        
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()
        
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        
        return jsonify({
            'cart_id': cart.id,
            'items': [cart_item_to_dict(item) for item in cart_items],
            'total_items': len(cart_items),
            'subtotal': sum(float(item.price) * item.quantity for item in cart_items)
        })
        
    except Exception as e:
        current_app.logger.error(f"Get cart error: {str(e)}")
        return jsonify({'error': 'Failed to get cart'}), 500

@cart_bp.route('/', methods=['POST'])
@jwt_required()
def add_to_cart():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('product_id') or not data.get('quantity'):
            return jsonify({'error': 'Product ID and quantity are required'}), 400
        
        # Get or create cart
        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()
        
        # Check product exists and has stock
        product = Product.query.filter_by(id=data['product_id'], is_active=True).first()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        if product.quantity < data['quantity']:
            return jsonify({'error': 'Insufficient stock'}), 400
        
        # Check if item already in cart
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=data['product_id']).first()
        
        if cart_item:
            cart_item.quantity += data['quantity']
        else:
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=data['product_id'],
                quantity=data['quantity'],
                price=product.price
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Product added to cart',
            'cart_item': cart_item_to_dict(cart_item)
        })
        
    except Exception as e:
        current_app.logger.error(f"Add to cart error: {str(e)}")
        return jsonify({'error': 'Failed to add product to cart'}), 500

@cart_bp.route('/<product_id>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(product_id):
    try:
        user_id = get_jwt_identity()
        cart = Cart.query.filter_by(user_id=user_id).first()
        
        if not cart:
            return jsonify({'error': 'Cart not found'}), 404
        
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        
        if not cart_item:
            return jsonify({'error': 'Item not found in cart'}), 404
        
        db.session.delete(cart_item)
        db.session.commit()
        
        return jsonify({'message': 'Item removed from cart'})
        
    except Exception as e:
        current_app.logger.error(f"Remove from cart error: {str(e)}")
        return jsonify({'error': 'Failed to remove item from cart'}), 500

@cart_bp.route('/<product_id>', methods=['PUT'])
@jwt_required()
def update_cart_item(product_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('quantity'):
            return jsonify({'error': 'Quantity is required'}), 400
        
        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            return jsonify({'error': 'Cart not found'}), 404
        
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if not cart_item:
            return jsonify({'error': 'Item not found in cart'}), 404
        
        # Check stock
        product = Product.query.get(product_id)
        if product.quantity < data['quantity']:
            return jsonify({'error': 'Insufficient stock'}), 400
        
        cart_item.quantity = data['quantity']
        db.session.commit()
        
        return jsonify({
            'message': 'Cart item updated',
            'cart_item': cart_item_to_dict(cart_item)
        })
        
    except Exception as e:
        current_app.logger.error(f"Update cart item error: {str(e)}")
        return jsonify({'error': 'Failed to update cart item'}), 500

def cart_item_to_dict(cart_item):
    return {
        'id': cart_item.id,
        'product_id': cart_item.product_id,
        'product_name': cart_item.product.name,
        'product_image': cart_item.product.images[0] if cart_item.product.images else None,
        'price': float(cart_item.price),
        'quantity': cart_item.quantity,
        'total': float(cart_item.price) * cart_item.quantity
    }