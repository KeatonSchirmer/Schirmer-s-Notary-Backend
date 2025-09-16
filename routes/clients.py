from flask import Blueprint, jsonify, request
from database.db import db
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from models.accounts import Client
from models.bookings import AcceptedBooking

clients_bp = Blueprint('contacts', __name__)


@clients_bp.route('/all', methods=['GET'])
def get_all_contacts():
    contacts = Client.query.order_by(Client.name).all()
    return jsonify({
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "company": getattr(c, "company", None)
            } for c in contacts
        ]
    })

@clients_bp.route('/clients', methods=['GET', 'POST'])
def get_contacts_visible_to_admin():
    accepted_bookings = AcceptedBooking.query.all()
    accepted_client_ids = {b.client_id for b in accepted_bookings}

    visible_contacts = Client.query.filter(Client.id.in_(accepted_client_ids)).all()
    
    return jsonify({
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "company": getattr(c, "company", None)
            } for c in visible_contacts
        ]
    })

@clients_bp.route('/<int:client_id>', methods=['GET', 'OPTIONS'])
def get_client(client_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    return jsonify({
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'company': getattr(client, "company", None)
    })

@clients_bp.route('/<int:client_id>/history', methods=['GET'])
def get_client_history(client_id):
    bookings = AcceptedBooking.query.filter_by(client_id=client_id).order_by(AcceptedBooking.date_time.desc()).all()
    return jsonify({
        'history': [
            {
                'id': b.id,
                'service': getattr(b, "service", None),
                'status': getattr(b, "status", None),
                'date_time': b.date_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(b.date_time, 'strftime') else str(b.date_time),
                'notes': getattr(b, "notes", None)
            } for b in bookings
        ]
    })

@clients_bp.route('/create', methods=['POST'])
def create_client():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    company = data.get('company')

    if not name or not email:
        return jsonify({'error': 'Name and email are required.'}), 400

    client = Client(name=name, email=email, company=company)
    db.session.add(client)
    db.session.commit()
    return jsonify({
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'company': client.company
    }), 201

@clients_bp.route('/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    return jsonify({'message': 'Contact deleted successfully.'}), 200

@clients_bp.route('/contact', methods=['POST'])
def send_contact_email():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    client_id = data.get('client_id')

    if not all([name, email, message]):
        return jsonify({'error': 'Missing required fields'}), 400

    client = None
    if client_id:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client not found'}), 404

    to_email = 'schirmer.nikolas@gmail.com'
    subject = f'New Contact Message from {name}'
    body = f"Name: {name}\nEmail: {email}\nMessage:\n{message}"
    if client:
        body += f"\n\nLinked Client ID: {client.id}\nClient Name: {client.name}\nClient Email: {client.email}"

    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = 'schirmer.nikolas@gmail.com'
    smtp_pass = 'cgyqzlbjwrftwqok'

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return jsonify({'message': 'Email sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500