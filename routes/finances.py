from flask import Blueprint, request, jsonify, session, redirect
import os
from database.db import db
from datetime import datetime
from models.business import Finance, Invoice, Billing
from models.accounts import Client
import random
import uuid
import string
import datetime
import requests

finances_bp = Blueprint('finances', __name__)

BASE_URL = os.environ.get('BASE_PUBLIC_API_URL')
SQUARE_ACCESS_TOKEN = os.environ.get('SQUARE_ACCESS_TOKEN')
PAYMENT_SESSIONS = {}

#* ============ Admin Finance Management ============

@finances_bp.route('/', methods=['GET'])
def get_finances():
    entries = Finance.query.order_by(Finance.date.desc()).all()
    return jsonify([entry.to_dict() for entry in entries])

@finances_bp.route('/add', methods=['POST'])
def add_finance():
    data = request.get_json()
    entry = Finance(
        type=data["type"],
        description=data.get("description", ""),
        amount=data["amount"],
        date=datetime.strptime(data["date"], "%Y-%m-%d")
    )
    db.session.add(entry)
    db.session.commit()
    db.session.refresh(entry)
    return jsonify(entry.to_dict())

@finances_bp.route('/<int:finance_id>', methods=['GET'])
def get_finance(finance_id):
    entry = Finance.query.get(finance_id)
    if not entry:
        return jsonify({"error": "Finance entry not found"}), 404
    return jsonify(entry.to_dict())

@finances_bp.route('/<int:finance_id>', methods=['PUT'])
def update_finance(finance_id):
    data = request.get_json()
    entry = Finance.query.get(finance_id)
    if not entry:
        return jsonify({"error": "Finance entry not found"}), 404
    entry.type = data.get("type", entry.type)
    entry.description = data.get("description", entry.description)
    entry.amount = data.get("amount", entry.amount)
    if "date" in data:
        entry.date = datetime.strptime(data["date"], "%Y-%m-%d")
    db.session.commit()
    db.session.refresh(entry)
    return jsonify(entry.to_dict())

@finances_bp.route('/<int:finance_id>', methods=['DELETE'])
def delete_finance(finance_id):
    entry = Finance.query.get(finance_id)
    if not entry:
        return jsonify({"error": "Finance entry not found"}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Deleted"})

#* ============ Client Invoicing and Payment =============
#! May delete this to integrate with Square

@finances_bp.route('/invoice/create', methods=['POST'])
def create_invoice():
    """Create a new invoice for a booking"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['client_id', 'client_name', 'client_email', 'service_type', 'total_amount']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create invoice
        invoice = Invoice(**data)
        
        # For now, we'll just return the invoice data
        # In a production app, you'd want to store this in a database
        
        return jsonify({
            "message": "Invoice created successfully",
            "invoice": invoice.to_dict()
        }), 201
        
    except Exception as e:
        print(f"Error creating invoice: {e}")
        return jsonify({"error": "Failed to create invoice"}), 500

@finances_bp.route('/invoice/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """Get invoice by ID"""
    # For now, return a placeholder response
    # In production, you'd fetch from database
    return jsonify({
        "invoice_id": invoice_id,
        "status": "pending",
        "message": "Invoice retrieval not fully implemented yet"
    }), 200

@finances_bp.route('/invoice', methods=['GET'])
def list_invoices():
    """List all invoices"""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    # For now, return empty list
    # In production, you'd fetch from database
    return jsonify({
        "invoices": [],
        "message": "Invoice listing not fully implemented yet"
    }), 200

@finances_bp.route('/invoice/<invoice_id>/pay', methods=['POST'])
def pay_invoice(invoice_id):
    """Process payment for an invoice"""
    try:
        data = request.get_json()
        payment_method = data.get('payment_method', 'card')
        
        # For now, just return success
        # In production, you'd integrate with payment processor
        
        return jsonify({
            "message": "Payment processed successfully",
            "invoice_id": invoice_id,
            "payment_method": payment_method,
            "status": "paid"
        }), 200
        
    except Exception as e:
        print(f"Error processing payment: {e}")
        return jsonify({"error": "Payment processing failed"}), 500    
    
@finances_bp.route('payment/subscription', methods=['POST'])
def process_subscription_payment():
    """Process subscription payment (placeholder for App Store compliance)"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        plan = data.get('plan')
        amount = data.get('amount')
        plan_name = data.get('plan_name')
        
        if not plan or not amount:
            return jsonify({
                "success": False,
                "message": "Plan and amount are required"
            }), 400
        
        # Generate a mock payment ID for tracking
        payment_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        
        # For App Store compliance, we don't actually process payments here
        # This is a placeholder that simulates successful payment processing
        return jsonify({
            "success": True,
            "payment_id": payment_id,
            "message": f"Payment processed for {plan_name}",
            "amount_charged": amount,
            "plan": plan,
            "user_id": user_id,
            "transaction_date": datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error processing subscription payment: {e}")
        return jsonify({
            "success": False,
            "message": "Payment processing failed. Please try again."
        }), 500

@finances_bp.route('/service', methods=['POST'])
def process_service_payment():
    """Process service payment (placeholder for App Store compliance)"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        amount = data.get('amount')
        payment_method = data.get('payment_method')
        
        if not booking_id or not amount:
            return jsonify({
                "success": False,
                "message": "Booking ID and amount are required"
            }), 400
        
        # Generate a mock payment ID for tracking
        payment_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        
        # For App Store compliance, we don't actually process payments here
        # This is a placeholder that simulates successful payment processing
        return jsonify({
            "success": True,
            "payment_id": payment_id,
            "message": "Service payment processed successfully",
            "amount_charged": amount,
            "booking_id": booking_id,
            "payment_method": payment_method,
            "user_id": user_id,
            "transaction_date": datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error processing service payment: {e}")
        return jsonify({
            "success": False,
            "message": "Payment processing failed. Please try again."
        }), 500

@finances_bp.route('/methods', methods=['GET'])
def get_payment_methods():
    """Get user's saved payment methods"""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        payment_methods = []
        
        if user_type == 'client':
            # Check for billing information
            billing = Billing.query.filter_by(client_id=user_id).first()
            if billing and billing.card_number:
                # Return masked card information and card_on_file_id if available
                payment_method = {
                    "id": "card_1",
                    "type": "card",
                    "last_four": billing.card_number[-4:] if len(billing.card_number) >= 4 else "****",
                    "expiry": billing.card_expir,
                    "default": True
                }
                # Add Square card_on_file_id if present in billing
                if hasattr(billing, "card_on_file_id") and billing.card_on_file_id:
                    payment_method["card_on_file_id"] = billing.card_on_file_id
                else:
                    # Placeholder for Square card ID, update as needed
                    payment_method["card_on_file_id"] = None
                payment_methods.append(payment_method)
        
        return jsonify({
            "payment_methods": payment_methods,
            "default_method": payment_methods[0]["id"] if payment_methods else None
        }), 200
        
    except Exception as e:
        print(f"Error fetching payment methods: {e}")
        return jsonify({"error": "Failed to fetch payment methods"}), 500

@finances_bp.route('/history', methods=['GET'])
def get_payment_history():
    """Get user's payment history"""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        # This would normally query a payments table
        # For now, return empty history as placeholder
        payment_history = []
        
        return jsonify({
            "payments": payment_history,
            "total_count": len(payment_history)
        }), 200
        
    except Exception as e:
        print(f"Error fetching payment history: {e}")
        return jsonify({"error": "Failed to fetch payment history"}), 500

#* ============ Square API =============
