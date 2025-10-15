import requests
import base64
from datetime import datetime
from app import db
from app.models import Payment, Order
import stripe
from flask import current_app

class PaymentService:
    @staticmethod
    def init_stripe():
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        return stripe
    
    @staticmethod
    def create_stripe_payment_intent(order, payment_method='card'):
        try:
            stripe = PaymentService.init_stripe()
            
            intent = stripe.PaymentIntent.create(
                amount=int(order.total_amount * 100),  # Convert to cents
                currency=order.currency.lower(),
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number
                },
                payment_method_types=[payment_method],
            )
            
            return intent
        except Exception as e:
            current_app.logger.error(f"Stripe payment intent creation failed: {str(e)}")
            raise
    
    @staticmethod
    def process_mpesa_payment(phone, amount, order):
        try:
            # Get M-Pesa access token
            access_token = PaymentService.get_mpesa_access_token()
            
            # M-Pesa STK Push
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{current_app.config['MPESA_SHORTCODE']}{current_app.config['MPESA_PASSKEY']}{timestamp}".encode()
            ).decode()
            
            payload = {
                "BusinessShortCode": current_app.config['MPESA_SHORTCODE'],
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone,
                "PartyB": current_app.config['MPESA_SHORTCODE'],
                "PhoneNumber": phone,
                "CallBackURL": current_app.config['MPESA_CALLBACK_URL'],
                "AccountReference": order.order_number,
                "TransactionDesc": f"Payment for order {order.order_number}"
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
                json=payload,
                headers=headers
            )
            
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"M-Pesa payment processing failed: {str(e)}")
            raise
    
    @staticmethod
    def get_mpesa_access_token():
        try:
            consumer_key = current_app.config['MPESA_CONSUMER_KEY']
            consumer_secret = current_app.config['MPESA_CONSUMER_SECRET']
            
            credentials = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}'
            }
            
            response = requests.get(
                'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials',
                headers=headers
            )
            
            return response.json()['access_token']
            
        except Exception as e:
            current_app.logger.error(f"M-Pesa access token retrieval failed: {str(e)}")
            raise