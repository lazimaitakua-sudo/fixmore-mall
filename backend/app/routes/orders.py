from flask import Blueprint, jsonify

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders/test')
def test_order():
    return jsonify({"message": "Orders route works!"})