from flask import Blueprint, jsonify, request, session, send_file
from datetime import datetime
from database.db import db
import os
from models.journal import PDF
from models.accounts import Client
from models.business import Finance, Mileage
from models.bookings import Booking

jobs_bp = Blueprint('jobs', __name__)

PDF_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'database', 'pdfs')
os.makedirs(PDF_FOLDER, exist_ok=True)

@jobs_bp.route('/', methods=['GET'])
def get_all_bookings():
    bookings = Booking.query.all()
    return jsonify([
        {
            "id": b.id,
            "client_id": b.client_id,
            "service": b.service,
            "urgency": b.urgency,
            "date": b.date.strftime("%Y-%m-%d") if b.date else None,
            "time": b.time.strftime("%H:%M") if b.time else None,
            "location": b.location,
            "notes": b.notes,
            "journal_id": b.journal_id,
            "status": b.status
        }
        for b in bookings
    ])

@jobs_bp.route('/request', methods=['POST'])
def request_booking():
    data = request.get_json()
    client_id = data.get('client_id')
    service = data.get('service')
    urgency = data.get('urgency', 'normal')
    date = data.get('date')
    time = data.get('time')
    location = data.get('location', '')
    notes = data.get('notes', '')
    journal_id = data.get('journal_id')

    if not all([client_id, service, date, time]):
        return jsonify({'error': 'Missing required fields'}), 400

    booking = Booking(
        client_id=client_id,
        service=service,
        urgency=urgency,
        date=datetime.strptime(date, "%Y-%m-%d"),
        time=datetime.strptime(time, "%H:%M").time(),
        location=location,
        notes=notes,
        journal_id=journal_id,
        status="pending"
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"message": "Booking request submitted successfully", "id": booking.id}), 201

# Accept a booking
@jobs_bp.route('/<int:booking_id>/accept', methods=['POST'])
def accept_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "accepted"
    db.session.commit()
    return jsonify({"message": "Booking accepted", "id": booking.id}), 200

# Deny a booking
@jobs_bp.route('/<int:booking_id>/deny', methods=['POST'])
def deny_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "denied"
    booking.notes = request.json.get('notes', booking.notes)
    db.session.commit()
    return jsonify({"message": "Booking denied", "id": booking.id}), 200

# Complete a booking
@jobs_bp.route('/<int:booking_id>/complete', methods=['POST'])
def complete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "completed"
    booking.journal_id = request.json.get('journal_id', booking.journal_id)
    db.session.commit()
    return jsonify({"message": "Booking marked as completed", "id": booking.id}), 200

# Edit a booking
@jobs_bp.route('/<int:booking_id>/edit', methods=['PATCH'])
def edit_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    data = request.get_json() or {}
    if 'service' in data:
        booking.service = data['service']
    if 'urgency' in data:
        booking.urgency = data['urgency']
    if 'date' in data:
        booking.date = datetime.strptime(data['date'], "%Y-%m-%d")
    if 'time' in data:
        booking.time = datetime.strptime(data['time'], "%H:%M").time()
    if 'location' in data:
        booking.location = data['location']
    if 'notes' in data:
        booking.notes = data['notes']
    if 'journal_id' in data:
        booking.journal_id = data['journal_id']
    db.session.commit()
    return jsonify({"message": "Booking updated"}), 200

# Delete a booking
@jobs_bp.route('/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Booking deleted"}), 200

# Get bookings by status
@jobs_bp.route('/pending', methods=['GET'])
def get_pending_bookings():
    bookings = Booking.query.filter_by(status="pending").all()
    return jsonify([{
        "id": b.id,
        "client_id": b.client_id,
        "service": b.service,
        "urgency": b.urgency,
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.time.strftime("%H:%M"),
        "location": b.location,
        "notes": b.notes,
        "journal_id": b.journal_id
    } for b in bookings])

@jobs_bp.route('/accepted', methods=['GET'])
def get_accepted_bookings():
    bookings = Booking.query.filter_by(status="accepted").all()
    return jsonify([{
        "id": b.id,
        "client_id": b.client_id,
        "service": b.service,
        "urgency": b.urgency,
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.time.strftime("%H:%M"),
        "location": b.location,
        "notes": b.notes,
        "journal_id": b.journal_id
    } for b in bookings])

@jobs_bp.route('/denied', methods=['GET'])
def get_denied_bookings():
    bookings = Booking.query.filter_by(status="denied").all()
    return jsonify([{
        "id": b.id,
        "client_id": b.client_id,
        "service": b.service,
        "urgency": b.urgency,
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.time.strftime("%H:%M"),
        "location": b.location,
        "notes": b.notes,
        "journal_id": b.journal_id
    } for b in bookings])

@jobs_bp.route('/completed', methods=['GET'])
def get_completed_bookings():
    bookings = Booking.query.filter_by(status="completed").all()
    return jsonify([{
        "id": b.id,
        "client_id": b.client_id,
        "service": b.service,
        "urgency": b.urgency,
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.time.strftime("%H:%M"),
        "location": b.location,
        "notes": b.notes,
        "journal_id": b.journal_id
    } for b in bookings])

# PDF upload/list/download (unchanged)
@jobs_bp.route('/pdfs/upload', methods=['POST'])
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

@jobs_bp.route('/pdfs', methods=['GET'])
def list_pdfs():
    user_id = request.headers.get("X-User-Id")
    pdfs = PDF.query.filter_by(user_id=user_id).all()
    return jsonify({
        "pdfs": [
            {"id": pdf.id, "filename": pdf.filename, "upload_time": getattr(pdf, "upload_time", None), "file_path": pdf.file_path}
            for pdf in pdfs
        ]
    })

@jobs_bp.route('/pdfs/<filename>', methods=['GET'])
def get_pdf(filename):
    pdf = PDF.query.filter_by(filename=filename).first()
    if pdf:
        return send_file(pdf.file_path, mimetype='application/pdf')
    return jsonify({"error": "PDF not found"}), 404