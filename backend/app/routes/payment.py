from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Payment, Order, User
from app.services.payment_service import PaymentService
import stripe

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/mpesa', methods=['POST'])
@jwt_required()
def initiate_mpesa_payment():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('order_id') or not data.get('phone'):
            return jsonify({'error': 'Order ID and phone number are required'}), 400
        
        order = Order.query.filter_by(id=data['order_id'], user_id=user_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        if order.payment_status == 'paid':
            return jsonify({'error': 'Order is already paid'}), 400
        
        # Format phone number (ensure it starts with 254)
        phone = data['phone']
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+254'):
            phone = phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone
        
        # Process M-Pesa payment
        mpesa_response = PaymentService.process_mpesa_payment(
            phone=phone,
            amount=order.total_amount,
            order=order
        )
        
        if mpesa_response.get('ResponseCode') == '0':
            # Create payment record
            payment = Payment(
                order_id=order.id,
                payment_method='mpesa',
                amount=order.total_amount,
                status='pending',
                gateway_transaction_id=mpesa_response.get('CheckoutRequestID'),
                gateway_response=mpesa_response
            )
            
            db.session.add(payment)
            order.payment_status = 'pending'
            db.session.commit()
            
            return jsonify({
                'message': 'M-Pesa payment initiated',
                'checkout_request_id': mpesa_response.get('CheckoutRequestID'),
                'response_description': mpesa_response.get('ResponseDescription')
            })
        else:
            return jsonify({
                'error': mpesa_response.get('ResponseDescription', 'M-Pesa payment failed')
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"M-Pesa payment error: {str(e)}")
        return jsonify({'error': 'M-Pesa payment failed'}), 500

@payments_bp.route('/stripe/create-payment-intent', methods=['POST'])
@jwt_required()
def create_stripe_payment_intent():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('order_id'):
            return jsonify({'error': 'Order ID is required'}), 400
        
        order = Order.query.filter_by(id=data['order_id'], user_id=user_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        if order.payment_status == 'paid':
            return jsonify({'error': 'Order is already paid'}), 400
        
        # Create Stripe payment intent
        payment_intent = PaymentService.create_stripe_payment_intent(order)
        
        # Create payment record
        payment = Payment(
            order_id=order.id,
            payment_method='card',
            amount=order.total_amount,
            status='pending',
            gateway_transaction_id=payment_intent['id'],
            gateway_response=payment_intent
        )
        
        db.session.add(payment)
        order.payment_status = 'pending'
        db.session.commit()
        
        return jsonify({
            'client_secret': payment_intent['client_secret'],
            'payment_intent_id': payment_intent['id']
        })
        
    except Exception as e:
        current_app.logger.error(f"Stripe payment intent error: {str(e)}")
        return jsonify({'error': 'Failed to create payment intent'}), 500

@payments_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        # Verify webhook signature
        stripe = PaymentService.init_stripe()
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
        
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            
            # Update payment and order status
            payment = Payment.query.filter_by(
                gateway_transaction_id=payment_intent['id']
            ).first()
            
            if payment:
                payment.status = 'paid'
                payment.order.payment_status = 'paid'
                payment.order.status = 'confirmed'
                db.session.commit()
                
                current_app.logger.info(f"Payment succeeded for order {payment.order.order_number}")
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            
            payment = Payment.query.filter_by(
                gateway_transaction_id=payment_intent['id']
            ).first()
            
            if payment:
                payment.status = 'failed'
                payment.failure_reason = payment_intent.get('last_payment_error', {}).get('message')
                db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Stripe webhook error: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@payments_bp.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    try:
        data = request.get_json()
        current_app.logger.info(f"M-Pesa callback received: {data}")
        
        # Parse M-Pesa callback
        callback_data = data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = callback_data.get('CheckoutRequestID')
        result_code = callback_data.get('ResultCode')
        result_desc = callback_data.get('ResultDesc')
        
        payment = Payment.query.filter_by(gateway_transaction_id=checkout_request_id).first()
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        if result_code == 0:
            # Payment successful
            payment.status = 'paid'
            payment.order.payment_status = 'paid'
            payment.order.status = 'confirmed'
            
            # Extract transaction details
            callback_metadata = callback_data.get('CallbackMetadata', {}).get('Item', [])
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    payment.gateway_transaction_id = item.get('Value')
                    break
        else:
            # Payment failed
            payment.status = 'failed'
            payment.failure_reason = result_desc
        
        payment.gateway_response = data
        db.session.commit()
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})
        
    except Exception as e:
        current_app.logger.error(f"M-Pesa callback error: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'}), 500

@payments_bp.route('/methods', methods=['GET'])
def get_payment_methods():
    try:
        methods = [
            {
                'id': 'mpesa',
                'name': 'M-Pesa',
                'description': 'Pay via M-Pesa mobile money',
                'icon': 'fas fa-mobile-alt',
                'supported_countries': ['Kenya'],
                'processing_fee': 0
            },
            {
                'id': 'card',
                'name': 'Credit/Debit Card',
                'description': 'Pay with Visa, Mastercard, or American Express',
                'icon': 'fas fa-credit-card',
                'supported_countries': ['All'],
                'processing_fee': 0.035  # 3.5%
            }
        ]
        
        return jsonify({'payment_methods': methods})
        
    except Exception as e:
        current_app.logger.error(f"Get payment methods error: {str(e)}")
        return jsonify({'error': 'Failed to fetch payment methods'}), 500