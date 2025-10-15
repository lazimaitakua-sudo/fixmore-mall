from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import Product, Category
from sqlalchemy import or_

products_bp = Blueprint('products', __name__)

@products_bp.route('/', methods=['GET'])
def get_products():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        category = request.args.get('category')
        search = request.args.get('search')
        featured = request.args.get('featured', type=bool)
        
        query = Product.query.filter_by(is_active=True)
        
        if category:
            query = query.filter(Product.category.has(name=category))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.tags.contains([search])
                )
            )
        
        if featured:
            query = query.filter_by(is_featured=True)
        
        products = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'products': [product_to_dict(p) for p in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {str(e)}")
        return jsonify({'error': 'Failed to fetch products'}), 500

@products_bp.route('/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.filter_by(id=product_id, is_active=True).first()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        return jsonify(product_to_dict(product))
        
    except Exception as e:
        current_app.logger.error(f"Error fetching product: {str(e)}")
        return jsonify({'error': 'Failed to fetch product'}), 500

@products_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.filter_by(is_active=True).all()
        return jsonify([category_to_dict(c) for c in categories])
        
    except Exception as e:
        current_app.logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({'error': 'Failed to fetch categories'}), 500

def product_to_dict(product):
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': float(product.price),
        'compare_price': float(product.compare_price) if product.compare_price else None,
        'images': product.images or [],
        'category': category_to_dict(product.category) if product.category else None,
        'quantity': product.quantity,
        'sku': product.sku,
        'is_featured': product.is_featured,
        'tags': product.tags or [],
        'specifications': product.specifications or {},
        'created_at': product.created_at.isoformat()
    }

def category_to_dict(category):
    return {
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'image_url': category.image_url,
        'product_count': len(category.products) if category.products else 0
    }