from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import db
from models.accounts import Admin, Client
import datetime
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import timedelta
import traceback
import os
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

auth_bp = Blueprint('auth', __name__, template_folder='frontend/templates')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET') 
SCOPES = ['https://www.googleapis.com/auth/calendar']

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
                existing_client.name = name  # Update name in case it's different
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
    
@auth_bp.route('/session')
def get_session_info():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id:
        return jsonify({'logged_in': False}), 401
    return jsonify({'logged_in': True, 'user_id': user_id, 'user_type': user_type})

@auth_bp.route('/profile', methods=['GET'])
def view_profile():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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

@auth_bp.route('/direct-deposit/info', methods=['GET'])
def get_direct_deposit_info():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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
        return jsonify({"message": "No direct deposit info found"}), 404
    
    return jsonify(direct_deposit.to_dict()), 200
    
@auth_bp.route('/direct-deposit/update', methods=['POST'])
def update_direct_deposit_info():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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
        return jsonify({"message": "No direct deposit info found"}), 404
    
    try:
        db.session.delete(direct_deposit)
        db.session.commit()
        return jsonify({"message": "Direct deposit info deleted successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@auth_bp.route('/billing/info', methods=['GET'])
def get_billing_info():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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
        return jsonify({"message": "No billing info found"}), 404
    
    return jsonify(billing.to_dict()), 200

@auth_bp.route('/billing/update', methods=['POST'])
def update_billing_info():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not user_type:
        return jsonify({"message": "Not logged in"}), 401

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
        return jsonify({"message": "No billing info found"}), 404
    
    try:
        db.session.delete(billing)
        db.session.commit()
        return jsonify({"message": "Billing info deleted successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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