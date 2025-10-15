from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Review, Product, Order, OrderItem
from app.utils.security import admin_required

reviews_bp = Blueprint('reviews', __name__)

@reviews_bp.route('/', methods=['POST'])
@jwt_required()
def create_review():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('product_id') or not data.get('rating'):
            return jsonify({'error': 'Product ID and rating are required'}), 400
        
        # Check if user has purchased the product
        has_purchased = Order.query.join(OrderItem).filter(
            Order.user_id == user_id,
            Order.payment_status == 'paid',
            OrderItem.product_id == data['product_id']
        ).first()
        
        if not has_purchased:
            return jsonify({'error': 'You can only review products you have purchased'}), 400
        
        # Check if user already reviewed this product
        existing_review = Review.query.filter_by(
            user_id=user_id,
            product_id=data['product_id']
        ).first()
        
        if existing_review:
            return jsonify({'error': 'You have already reviewed this product'}), 400
        
        review = Review(
            product_id=data['product_id'],
            user_id=user_id,
            rating=data['rating'],
            title=data.get('title'),
            comment=data.get('comment'),
            is_verified=True  # Since they purchased it
        )
        
        db.session.add(review)
        db.session.commit()
        
        return jsonify({
            'message': 'Review submitted successfully',
            'review': review_to_dict(review)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create review error: {str(e)}")
        return jsonify({'error': 'Failed to submit review'}), 500

@reviews_bp.route('/product/<product_id>', methods=['GET'])
def get_product_reviews(product_id):
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        reviews = Review.query.filter_by(
            product_id=product_id,
            is_approved=True
        ).order_by(Review.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Calculate average rating
        avg_rating = db.session.query(
            db.func.avg(Review.rating)
        ).filter_by(
            product_id=product_id,
            is_approved=True
        ).scalar() or 0
        
        rating_distribution = db.session.query(
            Review.rating,
            db.func.count(Review.id)
        ).filter_by(
            product_id=product_id,
            is_approved=True
        ).group_by(Review.rating).all()
        
        return jsonify({
            'reviews': [review_to_dict(review) for review in reviews.items],
            'average_rating': round(float(avg_rating), 1),
            'total_reviews': reviews.total,
            'rating_distribution': {str(rating): count for rating, count in rating_distribution},
            'pages': reviews.pages,
            'current_page': page
        })
        
    except Exception as e:
        current_app.logger.error(f"Get product reviews error: {str(e)}")
        return jsonify({'error': 'Failed to fetch reviews'}), 500

@reviews_bp.route('/<review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    try:
        user_id = get_jwt_identity()
        review = Review.query.get(review_id)
        
        if not review:
            return jsonify({'error': 'Review not found'}), 404
        
        # Users can only delete their own reviews unless admin
        user = db.session.get(User, user_id)
        if review.user_id != user_id and not user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(review)
        db.session.commit()
        
        return jsonify({'message': 'Review deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete review error: {str(e)}")
        return jsonify({'error': 'Failed to delete review'}), 500

@reviews_bp.route('/admin/pending', methods=['GET'])
@jwt_required()
@admin_required
def get_pending_reviews():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        reviews = Review.query.filter_by(is_approved=False).order_by(
            Review.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'reviews': [review_to_dict(review, include_user=True) for review in reviews.items],
            'total': reviews.total,
            'pages': reviews.pages,
            'current_page': page
        })
        
    except Exception as e:
        current_app.logger.error(f"Get pending reviews error: {str(e)}")
        return jsonify({'error': 'Failed to fetch pending reviews'}), 500

@reviews_bp.route('/admin/<review_id>/approve', methods=['PUT'])
@jwt_required()
@admin_required
def approve_review(review_id):
    try:
        review = Review.query.get(review_id)
        if not review:
            return jsonify({'error': 'Review not found'}), 404
        
        review.is_approved = True
        db.session.commit()
        
        return jsonify({'message': 'Review approved successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve review error: {str(e)}")
        return jsonify({'error': 'Failed to approve review'}), 500

def review_to_dict(review, include_user=False):
    data = {
        'id': review.id,
        'product_id': review.product_id,
        'rating': review.rating,
        'title': review.title,
        'comment': review.comment,
        'is_verified': review.is_verified,
        'created_at': review.created_at.isoformat()
    }
    
    if include_user:
        data['user'] = {
            'id': review.user.id,
            'first_name': review.user.first_name,
            'last_name': review.user.last_name
        }
    
    return data