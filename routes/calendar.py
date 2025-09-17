from flask import Blueprint, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from database.db import db
from models.accounts import Admin, SchirmersNotary
from models.bookings import Booking
from datetime import datetime, timedelta
import os

calendar_bp = Blueprint('calendar', __name__, template_folder='frontend/templates')

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'utils', 'credentials.json'
)

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
            'dateTime': event_data['start_datetime'],
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': event_data['end_datetime'],
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
    bookings = Booking.query.filter_by(status="accepted").all()
    return jsonify([{
        "id": b.id,
        "name": b.service,
        "date": b.date.strftime("%Y-%m-%d") if b.date else None,
        "time": b.time.strftime("%H:%M") if b.time else None,
        "location": b.location,
        "notes": b.notes,
        "client_id": b.client_id
    } for b in bookings])

@calendar_bp.route('/local', methods=['POST'])
def add_local_event():
    data = request.get_json()
    user = get_default_user()
    if not user:
        return jsonify({"error": "No booking user found"}), 404

    booking = Booking(
        client_id=data.get('client_id'),
        service=data.get('service'),
        urgency=data.get('urgency', 'normal'),
        date=datetime.strptime(data.get('date'), "%Y-%m-%d"),
        time=datetime.strptime(data.get('time'), "%H:%M").time(),
        location=data.get('location'),
        notes=data.get('notes'),
        status="accepted"
    )
    db.session.add(booking)
    db.session.commit()

    client_email = data.get('client_email')
    start_datetime = f"{booking.date.strftime('%Y-%m-%d')}T{booking.time.strftime('%H:%M')}"
    end_datetime = (datetime.combine(booking.date, booking.time) + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M')

    add_event_to_calendar({
        "name": booking.service,
        "id": booking.id,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "notes": booking.notes,
        "client_email": client_email
    })

    return jsonify({"message": "Booking added and sent to Google Calendar.", "id": booking.id}), 201

@calendar_bp.route('/local/<int:booking_id>', methods=['PUT'])
def edit_local_event(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    data = request.get_json()
    booking.service = data.get('service', booking.service)
    booking.date = datetime.strptime(data.get('date'), "%Y-%m-%d") if data.get('date') else booking.date
    booking.time = datetime.strptime(data.get('time'), "%H:%M").time() if data.get('time') else booking.time
    booking.location = data.get('location', booking.location)
    booking.notes = data.get('notes', booking.notes)
    booking.client_id = data.get('client_id', booking.client_id)
    db.session.commit()
    return jsonify({"message": "Booking updated."})

@calendar_bp.route('/local/<int:booking_id>', methods=['DELETE'])
def delete_local_event(booking_id):
    booking = Booking.query.get(booking_id)
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

@calendar_bp.route('/availability', methods=['GET'])
def get_company_availability():
    company = SchirmersNotary.query.first()
    if not company:
        return jsonify({"error": "No company found"}), 404
    return jsonify({
        "address": company.address,
        "office_start": company.office_start,
        "office_end": company.office_end,
        "available_days": company.available_days.split(",") if company.available_days else []
    })

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

    busy_times = []
    accepted_bookings = Booking.query.filter_by(status="accepted", date=datetime.strptime(date_str, "%Y-%m-%d")).all()
    for b in accepted_bookings:
        start_dt = datetime.combine(b.date, b.time)
        end_dt = start_dt + timedelta(minutes=30)
        busy_times.append((start_dt, end_dt))

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

@calendar_bp.route('/local/sync-to-google', methods=['POST'])
def sync_all_local_to_google():
    bookings = Booking.query.filter_by(status="accepted").all()
    synced = []
    for b in bookings:
        start_datetime = f"{b.date.strftime('%Y-%m-%d')}T{b.time.strftime('%H:%M')}"
        end_datetime = (datetime.combine(b.date, b.time) + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M')
        event_data = {
            "name": b.service,
            "id": b.id,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "notes": b.notes,
            "client_email": None
        }
        add_event_to_calendar(event_data)
        synced.append(b.id)
    return jsonify({"message": f"Synced {len(synced)} bookings to Google Calendar.", "synced_ids": synced})

@calendar_bp.route('/google-sync-to-local', methods=['GET','POST'])
def sync_google_to_local():
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=50, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])

    synced = []
    for event in events:
        summary = event.get('summary', 'No Title')
        start = event['start'].get('dateTime')
        end = event['end'].get('dateTime')
        notes = event.get('description', '')
        if start:
            start_dt = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
            date = start_dt.date()
            time = start_dt.time()
        else:
            continue

        existing = Booking.query.filter_by(date=date, time=time, service=summary).first()
        if not existing:
            booking = Booking(
                service=summary,
                date=date,
                time=time,
                notes=notes,
                status="accepted"
            )
            db.session.add(booking)
            synced.append(summary)
    db.session.commit()
    return jsonify({"message": f"Synced {len(synced)} Google events to local calendar.", "synced_events": synced})


