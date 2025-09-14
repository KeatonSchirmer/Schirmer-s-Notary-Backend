from flask import Blueprint, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from database.db import db
from models.event import Event
from models.job import AcceptedJob
from models.user import User
from datetime import datetime


calendar_bp = Blueprint('calendar', __name__, template_folder='frontend/templates')

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'backend/utils/credentials.json'

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

def block_unavailable_time(start_datetime, end_datetime, user_id):
    service = get_calendar_service()
    event = {
        'summary': 'Unavailable',
        'start': {'dateTime': start_datetime, 'timeZone': 'America/New_York'},
        'end': {'dateTime': end_datetime, 'timeZone': 'America/New_York'},
    }
    service.events().insert(calendarId='primary', body=event).execute()

@calendar_bp.route('/', methods=['GET'])
def get_events():
    service = get_calendar_service()
    events_result = service.events().list(calendarId='primary', maxResults=10, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    return jsonify({"events": events})

@calendar_bp.route('/availability', methods=['POST'])
def set_availability():
    user_id = request.headers.get("X-User-Id")
    data = request.get_json()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.office_start = data.get("officeStart")
    user.office_end = data.get("officeEnd")
    user.available_days = data.get("availableDays", [])
    db.session.commit()
    return jsonify({"message": "Availability saved."}), 200

@calendar_bp.route('/local', methods=['POST'])
def add_local_event():
    data = request.get_json()
    user = User.query.get(data.get('user_id'))
    if not user:
        return jsonify({"error": "User not found"}), 404

    available_days = user.available_days.split(",") if user.available_days else []
    event_day = datetime.fromisoformat(data.get('start_date')).strftime("%a")
    if available_days and event_day not in available_days:
        return jsonify({"error": "Event day not in user's available days"}), 400

    office_start = user.office_start or "00:00"
    office_end = user.office_end or "23:59"
    event_start_time = datetime.fromisoformat(data.get('start_date')).strftime("%H:%M")
    event_end_time = datetime.fromisoformat(data.get('end_date')).strftime("%H:%M")
    if not (office_start <= event_start_time <= office_end and office_start <= event_end_time <= office_end):
        return jsonify({"error": "Event time outside user's available hours"}), 400

    event = Event(
        title=data.get('title'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        location=data.get('location'),
        description=data.get('description'),
        user_id=data.get('user_id'),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({"message": "Local event added.", "id": event.id}), 201

@calendar_bp.route('/google-sync', methods=['POST'])
def google_sync():
    data = request.get_json()
    event = Event(
        title=data.get('title'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        location=data.get('location'),
        description=data.get('description'),
        user_id=data.get('user_id'),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({"message": "Google event synced and slot blocked."}), 201

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