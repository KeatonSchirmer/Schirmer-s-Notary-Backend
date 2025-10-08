from flask import Blueprint, jsonify, request, session, send_file
from datetime import datetime
from database.db import db
import smtplib
from email.mime.text import MIMEText
import os
import requests
from models.journal import PDF
from models.accounts import Client
from models.business import Finance, Mileage
from models.bookings import Booking
from routes.calendar import add_event_to_calendar

jobs_bp = Blueprint('jobs', __name__)

PDF_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'database', 'pdfs')
os.makedirs(PDF_FOLDER, exist_ok=True)

import requests

def send_push_notification(token, title, body):
    if not token:
        return
    message = {
        'to': token,
        'sound': 'default',
        'title': title,
        'body': body,
    }
    try:
        requests.post(
            'https://exp.host/--/api/v2/push/send',
            json=message,
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        print(f"Failed to send push notification: {e}")

def send_confirmation_email(to_email, name, service, date, time):
    subject = "Booking Confirmation"
    body = f"""Hello {name},

Thank you for booking with Schirmer's Notary!    

Your booking for {service} on {date} at {time} has been received.

As the sole notary I want to ensure you receive the best services possible.
I ask for your understanding and patience as I manage my schedule to accommodate all clients.
We will contact you soon with further details.

Thank you,
Schirmer's Notary
"""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = "no-reply@schirmersnotary.com"
    msg['To'] = to_email

    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')

    if not smtp_username or not smtp_password:
        print("Email credentials not configured")
        return

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(msg['From'], [msg['To']], msg.as_string())
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")

@jobs_bp.route('/', methods=['GET'])
def get_all_bookings():
    bookings = Booking.query.all()
    return jsonify({
        "jobs": [
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
                "status": b.status,
                "rating": b.rating,
                "feedback": b.feedback
            }
            for b in bookings
        ]
    })

#TODO: Need to integrate fixes to have notes not filled with other info
@jobs_bp.route('/request', methods=['POST'])
def request_booking():
    data = request.get_json()
    client_id = data.get('client_id')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')

    if not client_id and email:
        client = Client.query.filter_by(email=email).first()
        if not client:
            client = Client(name=name, email=email, phone=phone, password_hash=None)
            db.session.add(client)
            db.session.commit()
        client_id = client.id
    else:
        client = Client.query.get(client_id)

    service = data.get('service')
    urgency = data.get('urgency', 'normal')
    date = data.get('date')
    time = data.get('time')
    location = data.get('location', '')
    notes = data.get('notes', '')
    journal_id = data.get('journal_id')

    print(f"client_id={client_id}, service={service}, date={date}, time={time}")

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
    send_confirmation_email(email, name, service, date, time)

    if client and getattr(client, "push_token", None):
        send_push_notification(
            client.push_token,
            "Booking Submitted",
            f"Your booking for {service} on {date} at {time} was submitted."
        )

    from models.accounts import Admin
    admins = Admin.query.all()
    for admin in admins:
        if admin.push_token:
            send_push_notification(
                admin.push_token,
                "New Booking Request",
                f"{name} submitted a booking for {service} on {date} at {time}."
            )

    return jsonify({"message": "Booking request submitted successfully", "id": booking.id}), 201

@jobs_bp.route('/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return jsonify({
        "id": booking.id,
        "client_id": booking.client_id,
        "service": booking.service,
        "urgency": booking.urgency,
        "date": booking.date.strftime("%Y-%m-%d") if booking.date else None,
        "time": booking.time.strftime("%H:%M") if booking.time else None,
        "location": booking.location,
        "notes": booking.notes,
        "journal_id": booking.journal_id,
        "status": booking.status,
        "rating": booking.rating,
        "feedback": booking.feedback
    })

@jobs_bp.route('/<int:booking_id>/accept', methods=['POST'])
def accept_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "accepted"
    db.session.commit()
    add_event_to_calendar(booking)
    return jsonify({"message": "Booking accepted", "id": booking.id}), 200

@jobs_bp.route('/<int:booking_id>/deny', methods=['POST'])
def deny_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "denied"
    booking.notes = request.json.get('notes', booking.notes)
    db.session.commit()
    return jsonify({"message": "Booking denied", "id": booking.id}), 200

@jobs_bp.route('/<int:booking_id>/decline', methods=['POST'])
def decline_booking(booking_id):
    """Alternative endpoint for declining bookings (same as deny)"""
    return deny_booking(booking_id)

@jobs_bp.route('/<int:booking_id>/complete', methods=['POST'])
def complete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "completed"
    booking.journal_id = request.json.get('journal_id', booking.journal_id)
    db.session.commit()
    return jsonify({"message": "Booking marked as completed", "id": booking.id}), 200

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

@jobs_bp.route('/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Booking deleted"}), 200

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
        "journal_id": b.journal_id,
        "rating": b.rating,
        "feedback": b.feedback
    } for b in bookings])

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

@jobs_bp.route('/<int:booking_id>/feedback', methods=['POST'])
def submit_feedback(booking_id):
    """
    Submit feedback for a completed booking
    Expects: {"rating": 1-5, "feedback": "optional text"}
    """
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.status != "completed":
        return jsonify({"error": "Feedback can only be submitted for completed bookings"}), 400
    
    data = request.get_json()
    rating = data.get('rating')
    feedback = data.get('feedback', '')
    
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
    
    try:
        booking.rating = rating
        booking.feedback = feedback
        db.session.commit()
        
        from models.accounts import Admin
        admins = Admin.query.all()
        for admin in admins:
            if admin.push_token:
                send_push_notification(
                    admin.push_token,
                    "New Feedback Received",
                    f"New {rating}★ rating for {booking.service} booking"
                )
        
        return jsonify({
            "message": "Feedback submitted successfully",
            "booking_id": booking.id,
            "rating": rating,
            "feedback": feedback
        }), 200
        
    except Exception as e:
        print(f"Failed to submit feedback: {e}")
        return jsonify({"error": "Failed to submit feedback"}), 500

#! Don't really need this    
@jobs_bp.route('/create', methods=['POST'])
def create_booking():
    """Alternative endpoint for booking creation"""
    return request_booking()

@jobs_bp.route('/client/request', methods=['POST'])  
def client_request_booking():
    """Client-specific booking request endpoint"""
    return request_booking()

@jobs_bp.route('/company/requests/<company_name>', methods=['GET'])
def get_company_requests(company_name):
    """Get all requests for a specific company"""
    try:
        # Find all clients with matching company
        clients = Client.query.filter(
            Client.company.ilike(f'%{company_name}%')
        ).all()
        
        client_ids = [client.id for client in clients]
        
        # Get all bookings for these clients
        bookings = Booking.query.filter(
            Booking.client_id.in_(client_ids)
        ).all()
        
        requests_data = []
        for booking in bookings:
            requests_data.append({
                'id': booking.id,
                'client_id': booking.client_id,
                'service': booking.service,
                'status': booking.status,
                'date': booking.date,
                'time': booking.time,
                'location': booking.location,
                'document_type': booking.service,  # For compatibility
                'urgency': booking.urgency,
                'notes': booking.notes
            })
        
        return jsonify({
            'requests': requests_data,
            'company': company_name,
            'total_requests': len(requests_data)
        }), 200
        
    except Exception as e:
        print(f"Error fetching company requests: {e}")
        return jsonify({'error': 'Failed to fetch company requests', 'requests': []}), 500

   