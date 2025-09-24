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

auth_bp = Blueprint('auth', __name__, template_folder='frontend/templates')

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
            # Save push token if provided
            if 'push_token' in data:
                user.push_token = data['push_token']
        else:
            return jsonify({"message": "Unknown user type"}), 400

        db.session.commit()
        return jsonify({"message": "Profile updated successfully"}), 200
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

    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = 'schirmer.nikolas@gmail.com'
    smtp_password = 'cgyqzlbjwrftwqok'

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

