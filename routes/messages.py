from flask import Blueprint, render_template, request, jsonify, session
import datetime
from models.message import Message, ClientContact
from models.user import User
from database.db import db
import logging


messages_bp = Blueprint('messages', __name__, template_folder='frontend/templates')

logging.basicConfig(level=logging.DEBUG)

message_log = {}

@messages_bp.route('/')
def inbox():
    conversations = ...
    return render_template('inbox.html', conversations=conversations)

@messages_bp.route('/conversation/<int:client_id>', methods=['GET'])
def get_conversation(client_id):
    messages = Message.query.filter_by(client_id=client_id).order_by(Message.timestamp).all()

    # Mark unread messages as read
    for m in messages:
        if not m.from_admin and not m.is_read:
            m.is_read = True
    db.session.commit()

    return jsonify([
        {
            "content": m.content,
            "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "from_admin": m.from_admin
        }
        for m in messages
    ])

@messages_bp.route('/messages/new', methods=['GET', 'POST'])
def new_message():
    contacts = ...  # Your contact list
    if request.method == 'POST':
        # Save new message and redirect to conversation
        pass
    return render_template('new_message.html', contacts=contacts)

@messages_bp.route('/me', methods=['GET'])
def get_my_client_id():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(user_id)
    contact = ClientContact.query.filter_by(email=user.email).first()
    if not contact:
        return jsonify({'error': 'Contact not found'}), 404

    return jsonify({'client_id': contact.id})

@messages_bp.route('/conversation/<int:client_id>', methods=['POST'])
def send_message(client_id):
    print(f"[ROUTE_HIT] Received message POST for client {client_id}")
    data = request.get_json()
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)

    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    new_message = Message(
        content=data.get('content'),
        from_admin=is_admin,  
        client_id=client_id
    )
    db.session.add(new_message)
    db.session.commit()

    return jsonify({'message': 'Message sent'})

@messages_bp.route('/admin/unread-counts', methods=['GET'])
def get_unread_message_counts():
    counts = db.session.query(
        Message.client_id,
        db.func.count(Message.id)
    ).filter_by(from_admin=False, is_read=False).group_by(Message.client_id).all()

    return jsonify({client_id: count for client_id, count in counts})

@messages_bp.route('/client', methods=['GET'])
def get_client_messages():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(user_id)
    contact = ClientContact.query.filter_by(email=user.email).first()

    if not contact:
        return jsonify({'error': 'Contact not found'}), 404

    messages = Message.query.filter_by(client_id=contact.id).order_by(Message.timestamp.asc()).all()

    return jsonify([
        {
            "content": m.content,
            "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "from_admin": m.from_admin
        } for m in messages
    ])

