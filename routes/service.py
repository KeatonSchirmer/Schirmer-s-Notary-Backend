from flask import Blueprint, request, jsonify
from database.db import db
from datetime import datetime

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    service = db.Column(db.String(50), nullable=False)
    urgency = db.Column(db.String(20), nullable=False, default='normal')
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

service_bp = Blueprint('service', __name__)

@service_bp.route('/request', methods=['POST'])
def create_service_request():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    service = data.get('service')
    urgency = data.get('urgency', 'normal')
    notes = data.get('notes')
    if not all([name, email, service, urgency]):
        return jsonify({'error': 'Missing required fields'}), 400
    req = ServiceRequest(name=name, email=email, phone=phone, service=service, urgency=urgency, notes=notes)
    db.session.add(req)
    db.session.commit()
    return jsonify({'message': 'Service request submitted successfully', 'request_id': req.id}), 201
