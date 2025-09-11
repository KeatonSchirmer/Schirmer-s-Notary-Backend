from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['email'] = user.email
        session['is_premium'] = user.is_premium
        return jsonify({'message': 'Login successful', 'user_id': user.id, 'is_premium': user.is_premium}), 200
    return jsonify({'error': 'Invalid email or password'}), 401


# Admin-only registration route
@login_bp.route('/admin/register', methods=['POST'])
def admin_register():
    data = request.get_json()
    admin_token = data.get('admin_token')
    email = data.get('email')
    password = data.get('password')
    # Replace 'your-admin-token' with a secure value
    if admin_token != 'your-admin-token':
        return jsonify({'error': 'Unauthorized'}), 403
    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    user = User(email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Registration successful', 'user_id': user.id}), 201
