from flask import Blueprint, jsonify, request
from database.db import db
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import os
from models.accounts import Client
from models.bookings import Booking

clients_bp = Blueprint('clients', __name__)

def serialize_company(company):
    if not company:
        return None
    return {
        "id": company.id,
        "name": company.name,
        "address": company.address
    }

@clients_bp.route('/search', methods=['GET'])
def search_client_by_email():
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email required'}), 400
    client = Client.query.filter_by(email=email).first()
    if client:
        return jsonify({'id': client.id, 'name': client.name, 'email': client.email, 'phone': client.phone})
    return jsonify({'id': None})

@clients_bp.route('/all', methods=['GET'])
def get_all_contacts():
    contacts = Client.query.order_by(Client.name).all()
    return jsonify({
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "company": serialize_company(getattr(c, "company", None))
            } for c in contacts
        ]
    })

@clients_bp.route('/clients', methods=['GET', 'POST'])
def get_contacts_visible_to_admin():
    bookings = Booking.query.filter(Booking.status.in_(["accepted", "completed"])).all()
    client_ids = {b.client_id for b in bookings}
    visible_contacts = Client.query.filter(Client.id.in_(client_ids)).all()
    return jsonify({
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "company": serialize_company(getattr(c, "company", None))
            } for c in visible_contacts
        ]
    })

@clients_bp.route('/<int:client_id>', methods=['PUT'])
def edit_client(client_id):
    data = request.get_json()
    client = Client.query.get_or_404(client_id)

    client.name = data.get('name', client.name)
    client.address = data.get('address', client.address)
    client.email = data.get('email', client.email)
    client.phone = data.get('phone', client.phone)
    client.premium = data.get('premium', client.premium)

    company_name = data.get('company_name')
    company_address = data.get('company_address')
    if company_name:
        from models.accounts import Company
        company_obj = Company.query.filter_by(name=company_name).first()
        if not company_obj:
            company_obj = Company(name=company_name, address=company_address)
            db.session.add(company_obj)
            db.session.commit()
        client.company_id = company_obj.id

    db.session.commit()
    return jsonify({
        'id': client.id,
        'name': client.name,
        'address': client.address,
        'email': client.email,
        'phone': client.phone,
        'premium': client.premium,
        'company_id': client.company_id
    }), 200

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
        'company': serialize_company(getattr(client, "company", None))
    })

@clients_bp.route('/<int:client_id>/history', methods=['GET'])
def get_client_history(client_id):
    bookings = Booking.query.filter_by(client_id=client_id).order_by(Booking.date.desc(), Booking.time.desc()).all()
    return jsonify({
        'history': [
            {
                'id': b.id,
                'service': b.service,
                'status': b.status,
                'date': b.date.strftime('%Y-%m-%d') if b.date else None,
                'time': b.time.strftime('%H:%M') if b.time else None,
                'notes': b.notes
            } for b in bookings
        ]
    })

@clients_bp.route('/create', methods=['POST'])
def create_client():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    company_name = data.get('company_name')
    company_address = data.get('company_address')

    if not name or not email:
        return jsonify({'error': 'Name and email are required.'}), 400

    company_obj = None
    if company_name:
        from models.accounts import Company 
        company_obj = Company.query.filter_by(name=company_name).first()
        if not company_obj:
            company_obj = Company(name=company_name, address=company_address)
            db.session.add(company_obj)
            db.session.commit()

    client = Client(
        name=name,
        email=email,
        company_id=company_obj.id if company_obj else None
    )
    db.session.add(client)
    db.session.commit()
    return jsonify({
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'company_id': client.company_id
    }), 201

@clients_bp.route('/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    return jsonify({'message': 'Contact deleted successfully.'}), 200

@clients_bp.route('/company/<company_name>', methods=['GET'])
def get_clients_by_company(company_name):
    """Get all clients for a specific company"""
    try:
        clients = Client.query.filter(
            Client.company.ilike(f'%{company_name}%')
        ).all()
        
        clients_data = []
        for client in clients:
            clients_data.append({
                'id': client.id,
                'name': client.name,
                'email': client.email,
                'phone': client.phone,
                'address': client.address,
                'company': client.company
            })
        
        return jsonify({
            'clients': clients_data,
            'company': company_name,
            'total_clients': len(clients_data)
        }), 200
        
    except Exception as e:
        print(f"Error fetching company clients: {e}")
        return jsonify({'error': 'Failed to fetch company clients', 'clients': []}), 500

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

    to_email = os.environ.get('CONTACT_EMAIL', 'schirmer.nikolas@gmail.com')
    subject = f'New Contact Message from {name}'
    body = f"Name: {name}\nEmail: {email}\nMessage:\n{message}"
    if client:
        body += f"\n\nLinked Client ID: {client.id}\nClient Name: {client.name}\nClient Email: {client.email}"

    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USERNAME')
    smtp_pass = os.environ.get('SMTP_PASSWORD')

    if not smtp_user or not smtp_pass:
        return jsonify({'error': 'Email service not configured'}), 500

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