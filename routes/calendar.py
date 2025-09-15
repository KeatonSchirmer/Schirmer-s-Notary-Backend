from flask import Blueprint, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from database.db import db
from models.event import Event
from models.user import User
from datetime import datetime, timedelta

calendar_bp = Blueprint('calendar', __name__, template_folder='frontend/templates')

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'backend/utils/credentials.json'

def get_default_user():
    return User.query.first()

def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    return service

def add_event_to_calendar(event_data):
    service = get_calendar_service()
    event = {
        'summary': event_data['title'],
        'location': event_data['location'],
        'description': event_data['description'],
        'start': {
            'dateTime': event_data['start_date'],
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': event_data['end_date'],
            'timeZone': 'America/New_York',
        },
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event

@calendar_bp.route('/', methods=['GET'])
def get_events():
    service = get_calendar_service()
    events_result = service.events().list(calendarId='primary', maxResults=10, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    return jsonify({"events": events})

@calendar_bp.route('/local', methods=['GET'])
def get_local_events():
    user_id = request.headers.get("X-User-Id")
    events = Event.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "id": e.id,
        "title": e.title,
        "start_date": e.start_date.isoformat(),
        "end_date": e.end_date.isoformat(),
        "location": e.location,
        "description": e.description,
        "user_id": e.user_id
    } for e in events])

@calendar_bp.route('/availability', methods=['POST'])
def set_availability():
    user_id = request.headers.get("X-User-Id")
    data = request.get_json()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.office_start = data.get("officeStart")
    user.office_end = data.get("officeEnd")
    days = data.get("availableDays", [])
    if isinstance(days, list):
        user.available_days = ",".join(str(d) for d in days)
    else:
        user.available_days = days
    db.session.commit()
    return jsonify({"message": "Availability saved."}), 200

@calendar_bp.route('/local', methods=['POST'])
def add_local_event():
    data = request.get_json()
    user = get_default_user()
    if not user:
        return jsonify({"error": "No booking user found"}), 404

    available_days = user.available_days.split(",") if user.available_days else []
    event_day = datetime.fromisoformat(data.get('start_date')).strftime("%a")
    if available_days and event_day not in available_days:
        return jsonify({"error": "Event day not in available days"}), 400

    office_start = user.office_start or "00:00"
    office_end = user.office_end or "23:59"
    event_start_time = datetime.fromisoformat(data.get('start_date')).strftime("%H:%M")
    event_end_time = datetime.fromisoformat(data.get('end_date')).strftime("%H:%M")
    if not (office_start <= event_start_time <= office_end and office_start <= event_end_time <= office_end):
        return jsonify({"error": "Event time outside available hours"}), 400

    event = Event(
        title=data.get('title'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        location=data.get('location'),
        description=data.get('description'),
        user_id=user.id,
    )
    db.session.add(event)
    db.session.commit()

    add_event_to_calendar({
        "title": event.title,
        "start_date": event.start_date if isinstance(event.start_date, str) else event.start_date.isoformat(),
        "end_date": event.end_date if isinstance(event.end_date, str) else event.end_date.isoformat(),
        "location": event.location,
        "description": event.description,
    })

    return jsonify({"message": "Appointment booked and sent to Google Calendar.", "id": event.id}), 201

@calendar_bp.route('/local/<int:event_id>', methods=['PUT'])
def edit_local_event(event_id):
    data = request.get_json()
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    event.title = data.get('title', event.title)
    event.start_date = data.get('start_date', event.start_date)
    event.end_date = data.get('end_date', event.end_date)
    event.location = data.get('location', event.location)
    event.description = data.get('description', event.description)
    db.session.commit()
    return jsonify({"message": "Local event updated."})

@calendar_bp.route('/local/<int:event_id>', methods=['DELETE'])
def delete_local_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": "Local event deleted."})

@calendar_bp.route('/slots', methods=['GET'])
def get_available_slots():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing date"}), 400

    user = get_default_user()
    if not user or not user.office_start or not user.office_end or not user.available_days:
        return jsonify({"slots": []})

    available_days = user.available_days.split(",") if isinstance(user.available_days, str) else user.available_days
    day_name = datetime.strptime(date_str, "%a")
    if day_name not in available_days:
        return jsonify({"slots": []})

    office_start = datetime.strptime(f"{date_str} {user.office_start}", "%Y-%m-%d %H:%M")
    office_end = datetime.strptime(f"{date_str} {user.office_end}", "%Y-%m-%d %H:%M")
    slot_length = timedelta(minutes=30)
    slots = []
    current = office_start
    while current + slot_length <= office_end:
        slots.append({
            "start": current.strftime("%Y-%m-%dT%H:%M"),
            "end": (current + slot_length).strftime("%Y-%m-%dT%H:%M")
        })
        current += slot_length

    events = Event.query.filter(
        Event.user_id == user.id,
        Event.start_date >= office_start,
        Event.end_date <= office_end
    ).all()
    busy_times = [(e.start_date, e.end_date) for e in events]

    def is_free(slot_start, slot_end):
        for busy_start, busy_end in busy_times:
            if not (slot_end <= busy_start or slot_start >= busy_end):
                return False
        return True

    available_slots = [
        slot for slot in slots
        if is_free(datetime.strptime(slot["start"], "%Y-%m-%dT%H:%M"),
                   datetime.strptime(slot["end"], "%Y-%m-%dT%H:%M"))
    ]

    return jsonify({"slots": available_slots})

@calendar_bp.route('/google-sync-events', methods=['POST'])
def sync_google_events():
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=50,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    google_events = events_result.get('items', [])

    synced = 0
    for ge in google_events:
        # Parse Google event start/end times
        start_dt = ge['start'].get('dateTime') or ge['start'].get('date')
        end_dt = ge['end'].get('dateTime') or ge['end'].get('date')
        exists = Event.query.filter_by(
            start_date=start_dt,
            end_date=end_dt,
            title=ge.get('summary')
        ).first()
        if not exists:
            event = Event(
                title=ge.get('summary'),
                start_date=start_dt,
                end_date=end_dt,
                location=ge.get('location'),
                description=ge.get('description'),
                user_id=request.headers.get("X-User-Id")
            )
            db.session.add(event)
            synced += 1
    db.session.commit()
    return jsonify({"message": f"Synced {synced} new Google Calendar events."})