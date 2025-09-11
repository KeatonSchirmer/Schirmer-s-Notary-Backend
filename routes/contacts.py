
from flask import Blueprint, jsonify
from models.message import ClientContact
from models.job import JobRequest

clients_bp = Blueprint('contacts', __name__)

@clients_bp.route('/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    client = ClientContact.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    return jsonify({'message': 'Contact deleted successfully.'}), 200

@clients_bp.route('/all', methods=['GET'])
def get_all_contacts():
    contacts = ClientContact.query.order_by(ClientContact.name).all()
    return jsonify({
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "first_request_id": c.first_request_id
            } for c in contacts
        ]
    })

@clients_bp.route('/clients', methods=['GET', 'POST'])
def get_contacts_visible_to_admin():
    # Only show clients who have at least one accepted request
    accepted_requests = JobRequest.query.filter_by(status='accepted').all()
    accepted_client_ids = {req.client_id for req in accepted_requests}

    visible_contacts = ClientContact.query.filter(ClientContact.id.in_(accepted_client_ids)).all()
    
    return jsonify({
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "first_request_id": c.first_request_id
            } for c in visible_contacts
        ]
    })

@clients_bp.route('/<int:client_id>', methods=['GET', 'OPTIONS'])
def get_client(client_id):
    if flask.request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    client = ClientContact.query.get(client_id)
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    return jsonify({
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'first_request_id': client.first_request_id
    })

@clients_bp.route('/<int:client_id>/history', methods=['GET'])
def get_client_history(client_id):
    requests = JobRequest.query.filter_by(requested_by=client_id).order_by(JobRequest.created_at.desc()).all()
    return jsonify({
        'history': [
            {
                'id': r.id,
                'service': r.service,
                'status': r.status,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else None,
                'urgency': r.urgency,
                'notes': r.description
            } for r in requests
        ]
    })