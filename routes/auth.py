from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from models.user import User
from models.message import ClientContact, Message
from database.db import db
import datetime

auth_bp = Blueprint('auth', __name__, template_folder='frontend/templates')


@auth_bp.route('/login', methods=['POST'])
def login():
    form_type = 'login'
    if form_type == 'login':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        if role == 'admin':
            user = User.query.filter_by(email=email, is_admin=True).first()
        else:
            user = User.query.filter_by(email=email, is_admin=False).first()
        if user and check_password_hash(user.password_hash, password):
            session["username"] = user.name
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return jsonify({"message": "Login successful", "user_id": user.id, "token": "dummy-token"}), 200
        else:
            return jsonify({"message": "Invalid username / password"}), 401
        
@auth_bp.route('/register', methods=['POST'])
def register():
    form_type = 'register'
    if form_type == 'register':
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        if not name or not email or not password:
            return jsonify({"message": "Missing required fields"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Username already exists"}), 400
        hashed_password = generate_password_hash(password)
        new_user = User(
            name=name, 
            email=email, 
            password_hash=hashed_password, 
            role=role)
        db.session.add(new_user)
        db.session.commit()

        if new_user.role == 'client':
            contact = ClientContact(
                id=new_user.id,
                name=new_user.name,
                email=new_user.email,
                first_request_id=None
            )
            db.session.add(contact)
            db.session.commit()

            admin_msg = Message(
                client_id=new_user.id,
                content="Welcome! We received your registration. If you have any questions or concerns please contact us."
            )
            db.session.add(admin_msg)
            db.session.commit()

        return jsonify({"message": "User registered successfully"}), 201
    
@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop("username", None)
    session.pop("user_id", None)
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route('/session')
def get_session_info():
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    if not user_id:
        return jsonify({'logged_in': False}), 401
    return jsonify({'logged_in': True, 'user_id': user_id, 'is_admin': is_admin})

@auth_bp.route('/twofa', methods=['POST'])
def two_factor_auth():
    data = request.get_json()
    code = data.get('code')
    if code == '123456':
        session['twofa_verified'] = True
        return jsonify({'message': '2FA verified'}), 200
    return jsonify({'error': 'Invalid 2FA code'}), 401

@auth_bp.route('/twofa/status', methods=['GET'])
def twofa_status():
    from flask import session
    verified = session.get('twofa_verified', False)
    return {'twofa_verified': verified}, 200