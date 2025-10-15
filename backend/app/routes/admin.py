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
        
    except Exception as