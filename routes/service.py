from flask import Blueprint, request, jsonify, send_file
from database.db import db
from datetime import datetime
from models.job import PDF
import os

PDF_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'database', 'pdfs')
os.makedirs(PDF_FOLDER, exist_ok=True)

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

@service_bp.route('/pdfs/upload', methods=['POST'])
def upload_pdf():
    user_id = request.headers.get("X-User-Id")
    file = request.files['file']
    filename = file.filename
    save_path = os.path.join(PDF_FOLDER, filename)
    file.save(save_path)

    pdf_record = PDF(user_id=user_id, filename=filename, file_path=save_path)
    db.session.add(pdf_record)
    db.session.commit()

    return jsonify({"message": "PDF uploaded and saved."}), 201

@service_bp.route('/pdfs', methods=['GET'])
def list_pdfs():
    user_id = request.headers.get("X-User-Id")
    pdfs = PDF.query.filter_by(user_id=user_id).all()
    return jsonify({
        "pdfs": [
            {"id": pdf.id, "filename": pdf.filename, "upload_time": pdf.upload_time, "file_path": pdf.file_path}
            for pdf in pdfs
        ]
    })

@service_bp.route('/pdfs/<filename>', methods=['GET'])
def get_pdf(filename):
    pdf = PDF.query.filter_by(filename=filename).first()
    if pdf:
        return send_file(pdf.file_path, mimetype='application/pdf')
    return jsonify({"error": "PDF not found"}), 404

