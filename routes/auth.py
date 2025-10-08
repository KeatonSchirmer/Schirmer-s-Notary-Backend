from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import db
from models.accounts import Admin, Client, SchirmersNotary
from models.bookings import Booking
import datetime
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import timedelta
import traceback
import os
from google_auth_oauthlib.flow import Flow

auth_bp = Blueprint('auth', __name__, template_folder='frontend/templates')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET') 
SCOPES = ['https://www.googleapis.com/auth/calendar']
SUBSCRIPTION_PLANS = {
    "Business": {
        "name": "Business",
        "price": 25.00,
        "discount_percentage": 15,
        "features": [
            "15% discount on all services",
            "Priority booking",
            "Business invoicing",
            "Monthly usage reports"
        ]
    },
    "Premium": {
        "name": "Premium", 
        "price": 45.00,
        "discount_percentage": 25,
        "features": [
            "25% discount on all services",
            "Priority booking",
            "Business invoicing",
            "Dedicated support",
            "Monthly usage reports",
            "Bulk booking discounts"
        ]
    },
    "Corporate": {
        "name": "Corporate",
        "price": 75.00,
        "discount_percentage": 35,
        "features": [
            "35% discount on all services",
            "Priority booking",
            "Business invoicing", 
            "Dedicated support",
            "Monthly usage reports",
            "Bulk booking discounts",
            "Custom payment terms",
            "Account manager"
        ]
    },
    "Custom": {
        "name": "Custom",
        "price": 0.00,
        "discount_percentage": 45,
        "features": [
            "Up to 45% discount on all services",
            "Custom pricing",
            "Dedicated support",
            "Custom features",
            "Account manager"
        ]
    }
}

def require_admin():
    """Helper function to check if current user is admin"""
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id:
        return None
        
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            return None
    
    if user_type != 'admin':
        return None
    return user_id

def require_ceo():
    """Helper function to check if current user is CEO"""
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id:
        return None
        
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
            user_id = 1
        else:
            return None
    
    if user_type != 'admin':
        return None
    
    ceo_record = SchirmersNotary.query.first()
    if not ceo_record or ceo_record.ceo_admin_id != int(user_id):
        return None
    
    return user_id

def get_user_subscription_data(user_id):
    """Get subscription data from the client table in accounts model"""
    try:
        client = Client.query.get(user_id)
        if not client:
            return {
                "user_id": user_id,
                "isActive": False,
                "plan": "None",
                "discountPercentage": 0,
                "startDate": None,
                "endDate": None,
                "status": "inactive",
                "features": []
            }
        
        # Get subscription info from client's premium field
        plan_name = client.premium or "None"
        
        # Check if the plan is active (not "None")
        is_active = plan_name != "None"
        
        # Get plan details from SUBSCRIPTION_PLANS
        plan_details = SUBSCRIPTION_PLANS.get(plan_name, {})
        
        return {
            "user_id": user_id,
            "isActive": is_active,
            "plan": plan_name,
            "discountPercentage": plan_details.get("discount_percentage", 0),
            "price": plan_details.get("price", 0.0),
            "startDate": None,  # Could add subscription start date field to Client model
            "endDate": None,    # Could add subscription end date field to Client model
            "status": "active" if is_active else "inactive",
            "features": plan_details.get("features", [])
        }
        
    except Exception as e:
        print(f"Error getting subscription data from client table: {e}")
        return {
            "user_id": user_id,
            "isActive": False,
            "plan": "None",
            "discountPercentage": 0,
            "startDate": None,
            "endDate": None,
            "status": "inactive",
            "features": []
        }

def get_user_business_data(user_id):
    """Get business account data for a user"""
    try:
        user = Client.query.get(user_id)
        if not user:
            return {
                "user_id": user_id,
                "isBusinessAccount": False,
                "companyName": "",
                "taxId": "",
                "billingContact": "",
                "poNumber": "",
                "costCenter": "", 
                "department": ""
            }
        
        # Check if user has company_id (business account indicator)
        if user.company_id and user.company:
            return {
                "user_id": user_id,
                "isBusinessAccount": True,
                "companyName": user.company.name if user.company else "",
                "taxId": "",
                "billingContact": user.name,
                "poNumber": "",
                "costCenter": "",
                "department": ""
            }
        else:
            return {
                "user_id": user_id,
                "isBusinessAccount": False,
                "companyName": "",
                "taxId": "",
                "billingContact": "",
                "poNumber": "",
                "costCenter": "",
                "department": ""
            }
    except Exception as e:
        print(f"Error getting business data: {e}")
        return {
            "user_id": user_id,
            "isBusinessAccount": False,
            "companyName": "",
            "taxId": "",
            "billingContact": "",
            "poNumber": "",
            "costCenter": "",
            "department": ""
        }

#=========== ADMIN AND CLIENT ================

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    admin = Admin.query.filter_by(email=email).first()
    if admin and admin.password_hash and check_password_hash(admin.password_hash, password):
        session["username"] = admin.name
        session['user_id'] = admin.id
        session['user_type'] = 'admin'
        return jsonify({"message": "Login successful", "user_id": admin.id, "user_type": "admin"}), 200

    client = Client.query.filter_by(email=email).first()
    if client and client.password_hash and check_password_hash(client.password_hash, password):
        session["username"] = client.name
        session['user_id'] = client.id
        session['user_type'] = 'client'
        return jsonify({"message": "Login successful", "user_id": client.id, "user_type": "client"}), 200

    return jsonify({"message": "Invalid username / password"}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop("username", None)
    session.pop("user_id", None)
    session.pop("user_type", None)
    session.pop("twofa_verified", None)
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route('/session')
def get_session_info():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({'logged_in': False}), 401
        
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({'logged_in': False}), 401
                
    return jsonify({'logged_in': True, 'user_id': user_id, 'user_type': user_type})

@auth_bp.route('/profile', methods=['GET'])
def view_profile():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    if user_type == 'admin':
        user = Admin.query.get(user_id)
        if not user:
            return jsonify({"message": "Admin not found"}), 404
        return jsonify({
            "name": user.name,
            "email": user.email,
            "address": user.address,
            "license_number": user.license_number,
            "license_expiration": user.license_expiration,
            "two_factor_enabled": user.two_factor_enabled,
            "notification_enabled": user.notification_enabled
        })
    elif user_type == 'client':
        user = Client.query.get(user_id)
        if not user:
            return jsonify({"message": "Client not found"}), 404
        return jsonify({
            "name": user.name,
            "email": user.email,
            "address": user.address,
            "phone": user.phone,
            "company": user.company,
            "two_factor_enabled": user.two_factor_enabled
        })
    else:
        return jsonify({"message": "Unknown user type"}), 400

@auth_bp.route('/profile/update', methods=['PATCH'])
def update_profile():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    try:
        if user_type == 'admin':
            user = Admin.query.get(user_id)
            if not user:
                return jsonify({"message": "Admin not found"}), 404
            user.name = data.get('name', user.name)
            user.email = data.get('email', user.email)
            user.address = data.get('address', user.address)
            user.license_number = data.get('license_number', user.license_number)
            user.license_expiration = data.get('license_expiration', user.license_expiration)
            user.notification_enabled = data.get('notification_enabled', user.notification_enabled)
            # Save push token if provided
            if 'push_token' in data:
                user.push_token = data['push_token']
        elif user_type == 'client':
            user = Client.query.get(user_id)
            if not user:
                return jsonify({"message": "Client not found"}), 404
            user.name = data.get('name', user.name)
            user.email = data.get('email', user.email)
            user.address = data.get('address', user.address)
            user.phone = data.get('phone', user.phone)
            user.company = data.get('company', user.company)
            if 'push_token' in data:
                user.push_token = data['push_token']
        else:
            return jsonify({"message": "Unknown user type"}), 400

        db.session.commit()
        return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 

@auth_bp.route('/twofa/request', methods=['POST'])
def request_2fa():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"error": "Not logged in"}), 401

    user = Admin.query.get(user_id) if user_type == 'admin' else Client.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    code = ''.join(random.choices(string.digits, k=6))
    user.two_factor_code = code
    user.two_factor_code_created = datetime.datetime.utcnow()
    db.session.commit()

    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')

    if not smtp_user or not smtp_password:
        return jsonify({"error": "Email service not configured"}), 500

    subject = "Your 2FA Confirmation Code"
    body = f"Your confirmation code is: {code}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = user.email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, user.email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Failed to send email:", e)

    return jsonify({"message": "Confirmation code sent to your email."}), 200

@auth_bp.route('/twofa/confirm', methods=['POST'])
def confirm_2fa():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    code = request.json.get('code')
    if not user_id or not user_type or not code:
        return jsonify({"error": "Missing user or code"}), 400

    user = Admin.query.get(user_id) if user_type == 'admin' else Client.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.two_factor_code_created or \
       datetime.datetime.utcnow() - user.two_factor_code_created > timedelta(minutes=25):
        return jsonify({"error": "Code expired"}), 400

    if user.two_factor_code == code:
        user.two_factor_enabled = True
        user.two_factor_code = None
        user.two_factor_code_created = None
        db.session.commit()
        session['twofa_verified'] = True
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Invalid code"}), 400

@auth_bp.route('/twofa/status', methods=['GET'])
def twofa_status():
    verified = session.get('twofa_verified', False)
    return {'twofa_verified': verified}, 200

@auth_bp.route('/google/connect', methods=['GET'])
def connect_google_calendar():
    """Initiate Google Calendar OAuth flow"""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return jsonify({"error": "Google OAuth not configured"}), 500

    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [f"{os.environ.get('API_BASE_URL')}/auth/google/callback"]
                }
            },
            scopes=SCOPES
        )
        
        flow.redirect_uri = f"{os.environ.get('API_BASE_URL')}/auth/google/callback"
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=f"{user_id}:{user_type}"
        )
        
        return jsonify({"authorization_url": authorization_url}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to initiate OAuth: {str(e)}"}), 500

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        state = request.args.get('state')
        code = request.args.get('code')
        
        if not state or not code:
            return jsonify({"error": "Missing state or code"}), 400
            
        user_id, user_type = state.split(':')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [f"{os.environ.get('API_BASE_URL')}/auth/google/callback"]
                }
            },
            scopes=SCOPES
        )
        
        flow.redirect_uri = f"{os.environ.get('API_BASE_URL')}/auth/google/callback"
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        if user_type == 'admin':
            user = Admin.query.get(user_id)
        else:
            user = Client.query.get(user_id)
            
        if user:
            user.google_access_token = credentials.token
            user.google_refresh_token = credentials.refresh_token
            user.google_token_expires = credentials.expiry
            user.google_calendar_connected = True
            db.session.commit()
            
        return jsonify({"message": "Google Calendar connected successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"OAuth callback failed: {str(e)}"}), 500

@auth_bp.route('/google/disconnect', methods=['POST'])
def disconnect_google_calendar():
    """Disconnect Google Calendar"""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

    try:
        if user_type == 'admin':
            user = Admin.query.get(user_id)
        else:
            user = Client.query.get(user_id)
            
        if user:
            user.google_access_token = None
            user.google_refresh_token = None
            user.google_token_expires = None
            user.google_calendar_connected = False
            db.session.commit()
            
        return jsonify({"message": "Google Calendar disconnected"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to disconnect: {str(e)}"}), 500
 
@auth_bp.route('/preferences', methods=['GET'])
def get_user_preferences():
    """Get user preferences"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    # Return default preferences for now
    return jsonify({
        "notifications": True,
        "emailUpdates": True,
        "smsUpdates": False,
        "language": "en",
        "timezone": "America/Chicago"
    }), 200

@auth_bp.route('/preferences', methods=['POST'])
def update_user_preferences():
    """Update user preferences"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        
        # For now, just return success
        # In production, you'd save to database
        
        return jsonify({
            "message": "Preferences updated successfully",
            "preferences": data
        }), 200
        
    except Exception as e:
        print(f"Error updating preferences: {e}")
        return jsonify({"error": "Failed to update preferences"}), 500

@auth_bp.route('/profile/delete', methods=['DELETE'])
def delete_profile():
    """Delete user profile"""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

    try:
        if user_type == 'admin':
            user = Admin.query.get(user_id)
            if not user:
                return jsonify({"message": "Admin not found"}), 404
        elif user_type == 'client':
            user = Client.query.get(user_id)
            if not user:
                return jsonify({"message": "Client not found"}), 404
        else:
            return jsonify({"message": "Unknown user type"}), 400

        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        # Clear the session
        session.pop("username", None)
        session.pop("user_id", None)
        session.pop("user_type", None)
        session.pop("twofa_verified", None)
        
        return jsonify({"message": "Account deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting profile: {e}")
        return jsonify({"error": "Failed to delete account"}), 500


#=========== ADMINS ===============

@auth_bp.route('/direct-deposit/info', methods=['GET'])
def get_direct_deposit_info():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    from models.business import DirectDeposit
    direct_deposit = None
    if user_type == 'admin':
        direct_deposit = DirectDeposit.query.filter_by(admin_id=user_id).first()
    elif user_type == 'client':
        return jsonify({
            "user_type": "client",
            "payment_method": "billing", 
            "message": "Client payments are processed via billing. Use /auth/billing/info endpoint for payment details.",
            "redirect_to": "/auth/billing/info"
        }), 200
        
    if not direct_deposit:
        return jsonify({
            "message": "No direct deposit info found", 
            "has_setup": False,
            "bank_name": "",
            "account_type": "",
            "account_number": "",
            "routing_number": ""
        }), 200
    
    return jsonify(direct_deposit.to_dict()), 200
    
@auth_bp.route('/direct-deposit/update', methods=['POST'])
def update_direct_deposit_info():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    from models.business import DirectDeposit
    
    direct_deposit = None
    if user_type == 'admin':
        direct_deposit = DirectDeposit.query.filter_by(admin_id=user_id).first()
        if not direct_deposit:
            direct_deposit = DirectDeposit(admin_id=user_id)
    elif user_type == 'client':
        return jsonify({
            "error": "Clients use billing, not direct deposit. Use /auth/billing/update endpoint.",
            "redirect_to": "/auth/billing/update"
        }), 400
    
    try:
        direct_deposit.bank_name = data.get('bank_name', direct_deposit.bank_name)
        direct_deposit.account_type = data.get('account_type', direct_deposit.account_type)
        
        if 'account_number' in data:
            direct_deposit.account_number = data['account_number']
        if 'routing_number' in data:
            direct_deposit.routing_number = data['routing_number']
        
        db.session.add(direct_deposit)
        db.session.commit()
        return jsonify({"message": "Direct deposit info updated successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/direct-deposit/delete', methods=['DELETE'])
def delete_direct_deposit_info():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    from models.business import DirectDeposit
    direct_deposit = None
    if user_type == 'admin':
        direct_deposit = DirectDeposit.query.filter_by(admin_id=user_id).first()
    elif user_type == 'client':
        return jsonify({
            "error": "Clients use billing, not direct deposit. Use /auth/billing/delete endpoint.",
            "redirect_to": "/auth/billing/delete"
        }), 400
    
    if not direct_deposit:
        return jsonify({"message": "No direct deposit info to delete"}), 200
    
    try:
        db.session.delete(direct_deposit)
        db.session.commit()
        return jsonify({"message": "Direct deposit info deleted successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
@auth_bp.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get database statistics for Master Controls dashboard"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # Get stats from database
        total_users = Client.query.count() + Admin.query.count()
        total_admins = Admin.query.count()
        total_clients = Client.query.count()
        total_jobs = Booking.query.count()
        pending_jobs = Booking.query.filter_by(status='pending').count()
        completed_jobs = Booking.query.filter_by(status='completed').count()
        
        # Calculate total revenue (basic calculation - needs Finance model integration)
        completed_bookings = Booking.query.filter_by(status='completed').all()
        total_revenue = 0.0
        for booking in completed_bookings:
            # Check if booking has associated finance records
            if booking.finances:
                for finance in booking.finances:
                    total_revenue += float(getattr(finance, 'amount', 0) or 0)
        
        return jsonify({
            "total_users": total_users,
            "total_admins": total_admins,
            "total_clients": total_clients,
            "total_jobs": total_jobs,
            "pending_jobs": pending_jobs,
            "completed_jobs": completed_jobs,
            "total_revenue": f"{total_revenue:.2f}"
        }), 200
        
    except Exception as e:
        print(f"Error fetching admin stats: {e}")
        return jsonify({"error": "Failed to fetch statistics"}), 500

@auth_bp.route('/admin/admins/all', methods=['GET'])
def get_all_admins():
    """Get all admin users for employee management"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        admins = Admin.query.all()
        admin_list = []
        
        for admin in admins:
            admin_data = {
                "id": admin.id,
                "name": admin.name,
                "email": admin.email,
                "address": admin.address or "",
                "license_number": admin.license_number or "",
                "license_expiration": admin.license_expiration.isoformat() if admin.license_expiration else None,
                "two_factor_enabled": admin.two_factor_enabled or False,
                "notification_enabled": admin.notification_enabled or True,
                "account_status": getattr(admin, 'account_status', 'confirmed') if admin.password_hash else "pending",
                "created_at": admin.created_at.isoformat() if hasattr(admin, 'created_at') and admin.created_at else None,
                # Employee-specific fields for Master Controls
                    "employment_type": getattr(admin, 'employment_type', 'full_time'),
                    "salary": float(getattr(admin, 'salary', 0.0) or 0.0),
                    "hourly_rate": float(getattr(admin, 'hourly_rate', 0.0) or 0.0),
                    "hours_per_week": getattr(admin, 'hours_per_week', 40),
                    "pay_period_start": getattr(admin, 'pay_period_start', None),
                    "pay_period_end": getattr(admin, 'pay_period_end', None),
                    "availability": getattr(admin, 'availability', {})
            }
            admin_list.append(admin_data)
            
        return jsonify({"admins": admin_list}), 200
        
    except Exception as e:
        print(f"Error fetching admins: {e}")
        return jsonify({"error": "Failed to fetch admin users"}), 500

@auth_bp.route('/admin/admins/create', methods=['POST'])
def create_admin():
    """Create new admin user via Master Controls"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        
        if not name or not email:
            return jsonify({"error": "Name and email are required"}), 400
            
        # Check if admin with this email already exists
        existing_admin = Admin.query.filter_by(email=email).first()
        if existing_admin:
            return jsonify({"error": "Admin with this email already exists"}), 409
            
        # Create new admin (no password initially - will be set via email confirmation)
        new_admin = Admin(
            name=name,
            email=email,
            address=data.get('address', ''),
            license_number=data.get('license_number', ''),
            license_expiration=datetime.datetime.fromisoformat(data['license_expiration']).date() if data.get('license_expiration') else None,
            two_factor_enabled=False,
            notification_enabled=True,
            account_status='pending'
        )
        
        # Add employee-specific fields if provided
        if 'employment_type' in data:
            new_admin.employment_type = data['employment_type']
        if 'salary' in data:
            new_admin.salary = float(data['salary'])
        if 'hourly_rate' in data:
            new_admin.hourly_rate = float(data['hourly_rate'])
        if 'hours_per_week' in data:
            new_admin.hours_per_week = int(data['hours_per_week'])
        if 'availability' in data:
            new_admin.availability = data['availability']
            
        db.session.add(new_admin)
        db.session.commit()
        
        # TODO: Send invitation email here
        
        return jsonify({
            "message": "Admin created successfully",
            "admin_id": new_admin.id,
            "status": "invitation_sent"
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin: {e}")
        return jsonify({"error": "Failed to create admin"}), 500

@auth_bp.route('/admin/admins/<int:admin_id>', methods=['PUT'])
def update_admin(admin_id):
    """Update admin user via Master Controls"""
    current_admin_id = require_admin()
    if not current_admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin not found"}), 404
            
        data = request.get_json()
        
        # Update basic fields
        if 'name' in data:
            admin.name = data['name']
        if 'email' in data:
            admin.email = data['email']
        if 'address' in data:
            admin.address = data['address']
        if 'license_number' in data:
            admin.license_number = data['license_number']
        if 'license_expiration' in data and data['license_expiration']:
            admin.license_expiration = datetime.datetime.fromisoformat(data['license_expiration']).date()
        if 'notification_enabled' in data:
            admin.notification_enabled = data['notification_enabled']
            
        # Update employee-specific fields
        if 'employment_type' in data:
            admin.employment_type = data['employment_type']
        if 'salary' in data:
            admin.salary = float(data['salary'])
        if 'hourly_rate' in data:
            admin.hourly_rate = float(data['hourly_rate'])
        if 'hours_per_week' in data:
            admin.hours_per_week = int(data['hours_per_week'])
        if 'pay_period_start' in data:
            admin.pay_period_start = data['pay_period_start']
        if 'pay_period_end' in data:
            admin.pay_period_end = data['pay_period_end']
        if 'availability' in data:
            admin.availability = data['availability']
            
        db.session.commit()
        
        return jsonify({"message": "Admin updated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating admin: {e}")
        return jsonify({"error": "Failed to update admin"}), 500

@auth_bp.route('/admin/admins/<int:admin_id>', methods=['DELETE'])
def delete_admin(admin_id):
    """Delete admin user via Master Controls"""
    current_admin_id = require_admin()
    if not current_admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    # Prevent self-deletion
    if current_admin_id == admin_id:
        return jsonify({"error": "Cannot delete your own account"}), 400
    
    try:
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin not found"}), 404
            
        db.session.delete(admin)
        db.session.commit()
        
        return jsonify({"message": "Admin deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting admin: {e}")
        return jsonify({"error": "Failed to delete admin"}), 500

@auth_bp.route('/admin/admins/<int:admin_id>/resend-invitation', methods=['POST'])
def resend_admin_invitation(admin_id):
    """Resend invitation email to admin"""
    current_admin_id = require_admin()
    if not current_admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin not found"}), 404
            
        if admin.password_hash:
            return jsonify({"error": "Admin account is already confirmed"}), 400
            
        # TODO: Implement email sending logic here
        # For now, just return success
        
        return jsonify({"message": "Invitation email sent successfully"}), 200
        
    except Exception as e:
        print(f"Error resending invitation: {e}")
        return jsonify({"error": "Failed to resend invitation"}), 500


#=========== CLIENTS ================

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"message": "Name, email, and password are required"}), 400

    existing_client = Client.query.filter_by(email=email).first()
    
    if existing_client:
        if not existing_client.password_hash:
            try:
                existing_client.name = name
                existing_client.password_hash = generate_password_hash(password)
                db.session.commit()
                
                session["username"] = existing_client.name
                session['user_id'] = existing_client.id
                session['user_type'] = 'client'
                
                return jsonify({
                    "message": "Password added to existing account", 
                    "user_id": existing_client.id, 
                    "user_type": "client"
                }), 200
                
            except Exception as e:
                traceback.print_exc()
                return jsonify({"error": "Failed to add password to account"}), 500
        else:
            return jsonify({"message": "Account with this email already exists"}), 409

    try:
        password_hash = generate_password_hash(password)
        new_client = Client(
            name=name,
            email=email,
            password_hash=password_hash
        )
        
        db.session.add(new_client)
        db.session.commit()
        
        session["username"] = new_client.name
        session['user_id'] = new_client.id
        session['user_type'] = 'client'
        
        return jsonify({
            "message": "Registration successful", 
            "user_id": new_client.id, 
            "user_type": "client"
        }), 201
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Registration failed"}), 500
   
@auth_bp.route('/billing/info', methods=['GET'])
def get_billing_info():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    from models.business import Billing
    billing = None
    if user_type == 'admin':
        return jsonify({
            "user_type": "admin",
            "payment_method": "direct_deposit", 
            "message": "Admin payments are processed via direct deposit. Use /auth/direct-deposit/info endpoint for payment details.",
            "redirect_to": "/auth/direct-deposit/info"
        }), 200
    elif user_type == 'client':
        billing = Billing.query.filter_by(client_id=user_id).first()
    
    if not billing:
        return jsonify({
            "message": "No billing info found",
            "has_setup": False,
            "address": "",
            "city": "",
            "state": "",
            "zip_code": "",
            "country": "",
            "tax_id": "",
            "payment_method": "",
            "card_expir": "",
            "card_cvv": "",
            "card_number": ""
        }), 200
    
    return jsonify(billing.to_dict()), 200

@auth_bp.route('/billing/update', methods=['POST'])
def update_billing_info():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    from models.business import Billing
    
    billing = None
    if user_type == 'admin':
        return jsonify({
            "error": "Admins use direct deposit, not billing. Use /auth/direct-deposit/update endpoint.",
            "redirect_to": "/auth/direct-deposit/update"
        }), 400
    elif user_type == 'client':
        billing = Billing.query.filter_by(client_id=user_id).first()
        if not billing:
            billing = Billing(client_id=user_id)
    
    try:
        billing.address = data.get('address', billing.address)
        billing.city = data.get('city', billing.city)
        billing.state = data.get('state', billing.state)
        billing.zip_code = data.get('zip_code', billing.zip_code)
        billing.country = data.get('country', billing.country)
        billing.payment_method = data.get('payment_method', billing.payment_method)
        billing.card_expir = data.get('card_expir', billing.card_expir)
        
        if 'tax_id' in data:
            billing.tax_id = data['tax_id']
        if 'card_number' in data:
            billing.card_number = data['card_number']
        if 'card_cvv' in data:
            billing.card_cvv = data['card_cvv']
        
        db.session.add(billing)
        db.session.commit()
        return jsonify({"message": "Billing info updated successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/billing/delete', methods=['DELETE'])
def delete_billing_info():
    user_id = request.headers.get('X-User-Id') or session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401
    
    # If user_type is not in session, determine it by checking if user exists as admin or client
    if not user_type:
        admin_user = Admin.query.get(user_id)
        if admin_user:
            user_type = 'admin'
        else:
            client_user = Client.query.get(user_id)
            if client_user:
                user_type = 'client'
            else:
                return jsonify({"message": "User not found"}), 404

    from models.business import Billing
    billing = None
    if user_type == 'admin':
        return jsonify({
            "error": "Admins use direct deposit, not billing. Use /auth/direct-deposit/delete endpoint.",
            "redirect_to": "/auth/direct-deposit/delete"
        }), 400
    elif user_type == 'client':
        billing = Billing.query.filter_by(client_id=user_id).first()
    
    if not billing:
        return jsonify({"message": "No billing info to delete"}), 200
    
    try:
        db.session.delete(billing)
        db.session.commit()
        return jsonify({"message": "Billing info deleted successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/subscription/<int:user_id>', methods=['GET'])
def get_user_subscription(user_id):
    """Get subscription information for a user"""
    try:
        subscription_data = get_user_subscription_data(user_id)
        return jsonify(subscription_data), 200
    except Exception as e:
        print(f"Error fetching subscription: {e}")
        return jsonify({"error": "Failed to fetch subscription"}), 500

@auth_bp.route('/subscription', methods=['GET'])
def get_current_user_subscription():
    """Get subscription for currently logged in user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        subscription_data = get_user_subscription_data(user_id)
        return jsonify(subscription_data), 200
    except Exception as e:
        print(f"Error fetching subscription: {e}")
        return jsonify({"error": "Failed to fetch subscription"}), 500

@auth_bp.route('/subscription/plans', methods=['GET'])
def get_subscription_plans():
    """Get available subscription plans"""
    return jsonify({"plans": SUBSCRIPTION_PLANS}), 200

@auth_bp.route('/subscription/update', methods=['POST'])
def update_subscription():
    """Update user subscription"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        plan_name = data.get('plan')
        
        if plan_name not in SUBSCRIPTION_PLANS and plan_name != "None":
            return jsonify({"error": "Invalid subscription plan"}), 400
        
        # Update the client's premium field in the database
        client = Client.query.get(user_id)
        if not client:
            return jsonify({"error": "Client not found"}), 404
            
        client.premium = plan_name
        db.session.commit()
        
        return jsonify({
            "message": f"Subscription updated to {plan_name}",
            "plan": plan_name,
            "status": "active" if plan_name != "None" else "inactive"
        }), 200
        
    except Exception as e:
        print(f"Error updating subscription: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to update subscription"}), 500

@auth_bp.route('/subscription/cancel', methods=['POST'])
def cancel_subscription():
    """Cancel user subscription"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        # Update the client's premium field to "None" to cancel subscription
        client = Client.query.get(user_id)
        if not client:
            return jsonify({"error": "Client not found"}), 404
            
        client.premium = "None"
        db.session.commit()
        
        return jsonify({
            "message": "Subscription cancelled successfully",
            "status": "cancelled"
        }), 200
        
    except Exception as e:
        print(f"Error cancelling subscription: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to cancel subscription"}), 500

@auth_bp.route('/subscription/usage', methods=['POST'])
def track_subscription_usage():
    """Track subscription usage for a booking"""
    try:
        data = request.get_json()
        
        # For now, just return success
        # In production, you'd track usage in database
        
        return jsonify({
            "message": "Usage tracked successfully",
            "client_id": data.get('client_id'),
            "booking_id": data.get('booking_id'),
            "service_amount": data.get('service_amount'),
            "discount_applied": data.get('discount_applied')
        }), 200
        
    except Exception as e:
        print(f"Error tracking usage: {e}")
        return jsonify({"error": "Failed to track usage"}), 500

@auth_bp.route('/business/<int:user_id>', methods=['GET'])
def get_user_business(user_id):
    """Get business account information for a user"""
    try:
        business_data = get_user_business_data(user_id)
        return jsonify(business_data), 200
    except Exception as e:
        print(f"Error fetching business data: {e}")
        return jsonify({"error": "Failed to fetch business data"}), 500

@auth_bp.route('/business', methods=['GET'])
def get_current_user_business():
    """Get business account for currently logged in user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        business_data = get_user_business_data(user_id)
        return jsonify(business_data), 200
    except Exception as e:
        print(f"Error fetching business data: {e}")
        return jsonify({"error": "Failed to fetch business data"}), 500

@auth_bp.route('/business/update', methods=['POST'])
def update_business_account():
    """Update business account information"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        
        # For now, just return success
        # In production, you'd update the database
        
        return jsonify({
            "message": "Business account updated successfully",
            "isBusinessAccount": data.get('isBusinessAccount', False),
            "companyName": data.get('companyName', '')
        }), 200
        
    except Exception as e:
        print(f"Error updating business account: {e}")
        return jsonify({"error": "Failed to update business account"}), 500


# ========== SYSTEM SETTINGS ENDPOINTS ==========
# TODO: None of these are implemented in the database yet

@auth_bp.route('/admin/settings', methods=['GET'])
def get_system_settings():
    """Get all system settings"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # TODO: Implement actual settings storage
        # For now, return default settings
        default_settings = [
            {"id": 1, "key": "business_name", "value": "Schirmer's Notary", "description": "Business name displayed in app and documents", "type": "string"},
            {"id": 2, "key": "business_phone", "value": "+1 (555) 123-4567", "description": "Primary business contact number", "type": "string"},
            {"id": 3, "key": "business_email", "value": "contact@schirmersnotary.com", "description": "Primary business email address", "type": "string"},
            {"id": 4, "key": "business_address", "value": "123 Main St, City, State 12345", "description": "Business mailing address", "type": "string"},
            {"id": 5, "key": "base_service_fee", "value": "25.00", "description": "Base fee for notary services ($)", "type": "number"},
            {"id": 6, "key": "travel_fee_per_mile", "value": "0.65", "description": "Travel fee per mile ($)", "type": "number"},
            {"id": 7, "key": "minimum_travel_fee", "value": "15.00", "description": "Minimum travel fee ($)", "type": "number"},
            {"id": 8, "key": "urgent_service_multiplier", "value": "1.5", "description": "Multiplier for urgent services", "type": "number"},
            {"id": 9, "key": "default_appointment_duration", "value": "60", "description": "Default appointment duration (minutes)", "type": "number"},
            {"id": 10, "key": "advance_booking_days", "value": "30", "description": "Maximum days in advance for booking", "type": "number"},
            {"id": 11, "key": "minimum_notice_hours", "value": "24", "description": "Minimum hours notice for booking", "type": "number"},
            {"id": 12, "key": "allow_weekend_bookings", "value": "true", "description": "Allow bookings on weekends", "type": "boolean"},
            {"id": 13, "key": "email_notifications", "value": "true", "description": "Send email notifications", "type": "boolean"},
            {"id": 14, "key": "push_notifications", "value": "true", "description": "Send push notifications", "type": "boolean"},
            {"id": 15, "key": "sms_notifications", "value": "false", "description": "Send SMS notifications", "type": "boolean"},
            {"id": 16, "key": "reminder_hours_before", "value": "24", "description": "Send reminders X hours before appointment", "type": "number"},
            {"id": 17, "key": "auto_backup_enabled", "value": "true", "description": "Automatically backup database daily", "type": "boolean"},
            {"id": 18, "key": "backup_retention_days", "value": "30", "description": "Keep backups for X days", "type": "number"},
            {"id": 19, "key": "maintenance_mode", "value": "false", "description": "Enable maintenance mode", "type": "boolean"},
            {"id": 20, "key": "debug_logging", "value": "false", "description": "Enable debug logging", "type": "boolean"},
            {"id": 21, "key": "require_2fa", "value": "false", "description": "Require 2FA for all users", "type": "boolean"},
            {"id": 22, "key": "session_timeout_minutes", "value": "60", "description": "Session timeout (minutes)", "type": "number"},
            {"id": 23, "key": "max_login_attempts", "value": "5", "description": "Maximum login attempts before lockout", "type": "number"},
            {"id": 24, "key": "lockout_duration_minutes", "value": "30", "description": "Account lockout duration (minutes)", "type": "number"}
        ]
        
        return jsonify({"settings": default_settings}), 200
        
    except Exception as e:
        print(f"Error fetching settings: {e}")
        return jsonify({"error": "Failed to fetch settings"}), 500

@auth_bp.route('/admin/settings/<int:setting_id>', methods=['PUT'])
def update_system_setting(setting_id):
    """Update a system setting"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        new_value = data.get('value')
        
        if new_value is None:
            return jsonify({"error": "Value is required"}), 400
            
        # TODO: Implement actual setting update in database
        # For now, just return success
        
        return jsonify({
            "message": "Setting updated successfully",
            "setting_id": setting_id,
            "new_value": new_value
        }), 200
        
    except Exception as e:
        print(f"Error updating setting: {e}")
        return jsonify({"error": "Failed to update setting"}), 500

@auth_bp.route('/admin/settings/reset', methods=['POST'])
def reset_system_settings():
    """Reset all settings to defaults"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # TODO: Implement actual settings reset in database
        
        return jsonify({"message": "Settings reset to defaults successfully"}), 200
        
    except Exception as e:
        print(f"Error resetting settings: {e}")
        return jsonify({"error": "Failed to reset settings"}), 500

@auth_bp.route('/admin/settings/export', methods=['GET'])
def export_system_settings():
    """Export system settings as JSON"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # Get current settings
        settings_response = get_system_settings()
        settings_data = settings_response[0].get_json()
        
        export_data = {
            "exported_at": datetime.datetime.now().isoformat(),
            "exported_by": admin_id,
            "settings": settings_data.get("settings", [])
        }
        
        return jsonify(export_data), 200
        
    except Exception as e:
        print(f"Error exporting settings: {e}")
        return jsonify({"error": "Failed to export settings"}), 500


# ========== BACKUP MANAGEMENT ENDPOINTS ==========
#TODO: None of these are implemented in the database/file system yet

@auth_bp.route('/admin/backups/list', methods=['GET'])
def get_backup_history():
    """Get backup history"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # TODO: Implement actual backup history from database/file system
        # For now, return mock data
        mock_backups = [
            {
                "id": 1,
                "filename": "backup_2025-01-07_10-30-00.sql",
                "size": "2.4 MB",
                "created_at": "2025-01-07T10:30:00Z",
                "type": "manual",
                "status": "completed"
            },
            {
                "id": 2, 
                "filename": "backup_2025-01-06_03-00-00.sql",
                "size": "2.3 MB",
                "created_at": "2025-01-06T03:00:00Z", 
                "type": "automatic",
                "status": "completed"
            }
        ]
        
        return jsonify({"backups": mock_backups}), 200
        
    except Exception as e:
        print(f"Error fetching backup history: {e}")
        return jsonify({"error": "Failed to fetch backup history"}), 500

@auth_bp.route('/admin/database/backup', methods=['POST'])
def create_database_backup():
    """Create new database backup"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # TODO: Implement actual database backup logic
        
        return jsonify({
            "message": "Database backup created successfully",
            "backup_id": "backup_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "status": "completed"
        }), 201
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        return jsonify({"error": "Failed to create backup"}), 500

@auth_bp.route('/admin/backups/<int:backup_id>', methods=['DELETE'])
def delete_backup(backup_id):
    """Delete a backup file"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # TODO: Implement actual backup file deletion
        
        return jsonify({"message": "Backup deleted successfully"}), 200
        
    except Exception as e:
        print(f"Error deleting backup: {e}")
        return jsonify({"error": "Failed to delete backup"}), 500

@auth_bp.route('/admin/database/restore/<int:backup_id>', methods=['POST'])
def restore_database_backup(backup_id):
    """Restore database from backup"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # TODO: Implement actual database restore logic
        
        return jsonify({
            "message": "Database restored successfully",
            "backup_id": backup_id,
            "status": "completed"
        }), 200
        
    except Exception as e:
        print(f"Error restoring backup: {e}")
        return jsonify({"error": "Failed to restore backup"}), 500

@auth_bp.route('/admin/system/reset', methods=['POST'])
def system_reset():
    """Reset entire system (DANGER)"""
    admin_id = require_admin()
    if not admin_id:
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # TODO: Implement actual system reset logic - this is dangerous!
        
        return jsonify({"message": "System reset completed successfully"}), 200
        
    except Exception as e:
        print(f"Error resetting system: {e}")
        return jsonify({"error": "Failed to reset system"}), 500


#========== SCHIRMER'S NOTARY SPECIFIC ==========

@auth_bp.route('/office/info', methods=['GET'])
def get_office_info():
    try:
        office = SchirmersNotary.query.first()
        
        if not office:
            return jsonify({
                "No office records found. Please set up office information.",
            }), 200
        
        office_data = {
            "id": office.id,
            "address": office.address,
            "phone": office.phone,
            "email": office.email,
            "office_start": getattr(office, 'office_start', '09:00'),
            "office_end": getattr(office, 'office_end', '17:00'),
            "available_days": getattr(office, 'available_days', 'Monday,Tuesday,Wednesday,Thursday,Friday')
        }
        
        return jsonify(office_data), 200
    
    except Exception as e:
        print(f"Error fetching office info: {e}")
        return jsonify({"error": "Failed to fetch office info"}), 500

@auth_bp.route('/office/update', methods=['POST'])
def update_office_info():
    admin_id = require_ceo()
    if not admin_id:
        return jsonify({"error": "CEO access required"}), 403
    
    try:
        office = SchirmersNotary.query.first()
        
        if not office:
            office = SchirmersNotary()
            db.session.add(office)
        
        data = request.get_json()
        
        if 'address' in data:
            office.address = data['address']
        if 'phone' in data:
            office.phone = data['phone']
        if 'email' in data:
            office.email = data['email']
        if 'office_start' in data:
            office.office_start = data['office_start']
        if 'office_end' in data:
            office.office_end = data['office_end']
        if 'available_days' in data:
            office.available_days = data['available_days']
            
        db.session.commit()
        
        updated_data = {
            "id": office.id,
            "address": office.address,
            "phone": office.phone,
            "email": office.email,
            "office_start": office.office_start,
            "office_end": office.office_end,
            "available_days": office.available_days
        }
        
        return jsonify({
            "message": "Office info updated successfully",
            "office": updated_data
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Error updating office info: {e}")
        return jsonify({"error": "Failed to update office info"}), 500
