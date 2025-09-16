from flask import Blueprint, jsonify, request, session, send_file
from datetime import datetime
from database.db import db
import os
from models.journal import PDF
from models.accounts import Client
from models.bookings import PendingBooking, AcceptedBooking, DeniedBooking, CompletedBooking

jobs_bp = Blueprint('jobs', __name__)

PDF_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'database', 'pdfs')
os.makedirs(PDF_FOLDER, exist_ok=True)

@jobs_bp.route('/request', methods=['POST'])
def request_job():
    data = request.get_json()
    name = data.get('name')
    service = data.get('service')
    urgency = data.get('urgency', 'normal')
    date = data.get('date')
    time = data.get('time')
    notes = data.get('notes', '')
    client_id = data.get('client_id')

    if not all([name, service, date, time, client_id]):
        return jsonify({'error': 'Missing required fields'}), 400

    booking = PendingBooking(
        name=name,
        service=service,
        urgency=urgency,
        date=datetime.strptime(date, "%Y-%m-%d"),
        time=time,
        notes=notes,
        client_id=client_id
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"message": "Job request submitted successfully", "id": booking.id}), 201

@jobs_bp.route('/pending/<int:booking_id>/accept', methods=['POST'])
def accept_booking(booking_id):
    booking = PendingBooking.query.get_or_404(booking_id)
    accepted = AcceptedBooking(
        name=booking.name,
        service=booking.service,
        urgency=booking.urgency,
        date=booking.date,
        time=booking.time,
        location=request.json.get('location', ''),
        notes=booking.notes,
        client_id=booking.client_id
    )
    db.session.add(accepted)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Booking accepted", "id": accepted.id}), 200

@jobs_bp.route('/pending/<int:booking_id>/deny', methods=['POST'])
def deny_booking(booking_id):
    booking = PendingBooking.query.get_or_404(booking_id)
    denied = DeniedBooking(
        name=booking.name,
        service=booking.service,
        date=booking.date,
        notes=request.json.get('notes', booking.notes),
        client_id=booking.client_id
    )
    db.session.add(denied)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Booking denied", "id": denied.id}), 200

@jobs_bp.route('/accepted/<int:booking_id>/complete', methods=['POST'])
def complete_booking(booking_id):
    booking = AcceptedBooking.query.get_or_404(booking_id)
    completed = CompletedBooking(
        name=booking.name,
        service=booking.service,
        date=booking.date,
        time=booking.time,
        location=booking.location,
        notes=booking.notes,
        client_id=booking.client_id,
        journal_id=request.json.get('journal_id'),
        mileage_id=request.json.get('mileage_id')
    )
    db.session.add(completed)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Booking marked as completed", "id": completed.id}), 200

@jobs_bp.route('/pending', methods=['GET'])
def get_pending_bookings():
    bookings = PendingBooking.query.all()
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "service": b.service,
        "urgency": b.urgency,
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.time,
        "notes": b.notes,
        "client_id": b.client_id
    } for b in bookings])

@jobs_bp.route('/accepted', methods=['GET'])
def get_accepted_bookings():
    bookings = AcceptedBooking.query.all()
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "service": b.service,
        "urgency": b.urgency,
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.time,
        "location": b.location,
        "notes": b.notes,
        "client_id": b.client_id
    } for b in bookings])

@jobs_bp.route('/denied', methods=['GET'])
def get_denied_bookings():
    bookings = DeniedBooking.query.all()
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "service": b.service,
        "date": b.date.strftime("%Y-%m-%d"),
        "notes": b.notes,
        "client_id": b.client_id
    } for b in bookings])

@jobs_bp.route('/completed', methods=['GET'])
def get_completed_bookings():
    bookings = CompletedBooking.query.all()
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "service": b.service,
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.time,
        "location": b.location,
        "notes": b.notes,
        "client_id": b.client_id,
        "journal_id": b.journal_id,
        "mileage_id": b.mileage_id
    } for b in bookings])

@jobs_bp.route('/accepted/<int:booking_id>/edit', methods=['PATCH'])
def edit_accepted_booking(booking_id):
    booking = AcceptedBooking.query.get_or_404(booking_id)
    data = request.get_json() or {}
    if 'name' in data:
        booking.name = data['name']
    if 'service' in data:
        booking.service = data['service']
    if 'urgency' in data:
        booking.urgency = data['urgency']
    if 'date' in data:
        booking.date = datetime.strptime(data['date'], "%Y-%m-%d")
    if 'time' in data:
        booking.time = data['time']
    if 'location' in data:
        booking.location = data['location']
    if 'notes' in data:
        booking.notes = data['notes']
    db.session.commit()
    return jsonify({"message": "Accepted booking updated"}), 200

@jobs_bp.route('/pending/<int:booking_id>', methods=['DELETE'])
def delete_pending_booking(booking_id):
    booking = PendingBooking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Pending booking deleted"}), 200

@jobs_bp.route('/accepted/<int:booking_id>', methods=['DELETE'])
def delete_accepted_booking(booking_id):
    booking = AcceptedBooking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Accepted booking deleted"}), 200

@jobs_bp.route('/denied/<int:booking_id>', methods=['DELETE'])
def delete_denied_booking(booking_id):
    booking = DeniedBooking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Denied booking deleted"}), 200

@jobs_bp.route('/completed/<int:booking_id>', methods=['DELETE'])
def delete_completed_booking(booking_id):
    booking = CompletedBooking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Completed booking deleted"}), 200

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

