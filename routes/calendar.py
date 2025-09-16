from flask import Blueprint, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from database.db import db
from models.accounts import Admin, SchirmersNotary
from models.bookings import AcceptedBooking
from datetime import datetime, timedelta

calendar_bp = Blueprint('calendar', __name__, template_folder='frontend/templates')

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'backend/utils/credentials.json'

def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_default_user():
    return Admin.query.first()

def add_event_to_calendar(event_data):
    service = get_calendar_service()
    event = {
        'summary': event_data['name'],
        'description': f"Booking ID: {event_data['id']}\nNotes: {event_data.get('notes', '')}",
        'start': {
            'dateTime': event_data['date_time'],
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': event_data['end_time'],
            'timeZone': 'America/New_York',
        },
        'attendees': [
            {'email': event_data.get('client_email', '')}
        ] if event_data.get('client_email') else []
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event

@calendar_bp.route('/local', methods=['GET'])
def get_local_events():
    user = get_default_user()
    bookings = AcceptedBooking.query.filter_by(admin_id=user.id).all() if user else []
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "date_time": b.date_time.isoformat() if hasattr(b.date_time, 'isoformat') else str(b.date_time),
        "end_time": b.end_time.isoformat() if hasattr(b.end_time, 'isoformat') else str(b.end_time),
        "notes": b.notes,
        "client_id": b.client_id
    } for b in bookings])

@calendar_bp.route('/local', methods=['POST'])
def add_local_event():
    data = request.get_json()
    user = get_default_user()
    if not user:
        return jsonify({"error": "No booking user found"}), 404

    booking = AcceptedBooking(
        name=data.get('name'),
        date_time=data.get('date_time'),
        end_time=data.get('end_time'),
        notes=data.get('notes'),
        client_id=data.get('client_id'),
        admin_id=user.id
    )
    db.session.add(booking)
    db.session.commit()

    client_email = data.get('client_email')

    add_event_to_calendar({
        "name": booking.name,
        "id": booking.id,
        "date_time": booking.date_time if isinstance(booking.date_time, str) else booking.date_time.isoformat(),
        "end_time": booking.end_time if isinstance(booking.end_time, str) else booking.end_time.isoformat(),
        "notes": booking.notes,
        "client_email": client_email
    })

    return jsonify({"message": "Booking added and sent to Google Calendar.", "id": booking.id}), 201

@calendar_bp.route('/local/<int:booking_id>', methods=['PUT'])
def edit_local_event(booking_id):
    booking = AcceptedBooking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    data = request.get_json()
    booking.name = data.get('name', booking.name)
    booking.date_time = data.get('date_time', booking.date_time)
    booking.end_time = data.get('end_time', booking.end_time)
    booking.notes = data.get('notes', booking.notes)
    booking.client_id = data.get('client_id', booking.client_id)
    db.session.commit()
    return jsonify({"message": "Booking updated."})

@calendar_bp.route('/local/<int:booking_id>', methods=['DELETE'])
def delete_local_event(booking_id):
    booking = AcceptedBooking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": "Booking deleted."})

@calendar_bp.route('/availability', methods=['POST'])
def set_company_availability():
    data = request.get_json()
    company = SchirmersNotary.query.first()
    if not company:
        company = SchirmersNotary()

    company.address = data.get("address", company.address)
    company.office_start = data.get("office_start", company.office_start)
    company.office_end = data.get("office_end", company.office_end)
    days = data.get("available_days", company.available_days)
    if isinstance(days, list):
        company.available_days = ",".join(str(d) for d in days)
    else:
        company.available_days = days

    db.session.add(company)
    db.session.commit()
    return jsonify({"message": "Company availability saved."}), 200

@calendar_bp.route('/slots', methods=['GET'])
def get_available_slots():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing date"}), 400

    company = SchirmersNotary.query.first()
    if not company or not company.office_start or not company.office_end or not company.available_days:
        return jsonify({"slots": []})

    available_days = company.available_days.split(",") if isinstance(company.available_days, str) else company.available_days
    day_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%a")
    if day_name not in available_days:
        return jsonify({"slots": []})

    office_start = datetime.strptime(f"{date_str} {company.office_start}", "%Y-%m-%d %H:%M")
    office_end = datetime.strptime(f"{date_str} {company.office_end}", "%Y-%m-%d %H:%M")
    slot_length = timedelta(minutes=30)
    slots = []
    current = office_start
    while current + slot_length <= office_end:
        slots.append({
            "start": current.strftime("%Y-%m-%dT%H:%M"),
            "end": (current + slot_length).strftime("%Y-%m-%dT%H:%M")
        })
        current += slot_length

    busy_times = [
        (b.date_time, b.end_time)
        for b in AcceptedBooking.query.filter_by(date_time=date_str).all()
        if b.date_time and b.end_time
    ]

    def is_free(slot_start, slot_end):
        for busy_start, busy_end in busy_times:
            if not (slot_end <= busy_start or slot_start >= busy_end):
                return False
        return True

    available_slots = [
        {
            "id": f"{slot['start']}-{slot['end']}",
            "date": date_str,
            "time": slot["start"].split("T")[1],
            "available": True
        }
        for slot in slots
        if is_free(datetime.strptime(slot["start"], "%Y-%m-%dT%H:%M"),
                datetime.strptime(slot["end"], "%Y-%m-%dT%H:%M"))
    ]

    return jsonify({"slots": available_slots})

