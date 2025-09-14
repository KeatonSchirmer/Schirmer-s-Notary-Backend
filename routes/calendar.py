from flask import Blueprint, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from database.db import db
from models.event import Event
from models.job import AcceptedJob


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

@calendar_bp.route('/local', methods=['GET'])
def get_local_events():
    events = Event.query.all()
    return jsonify([{
        "id": e.id,
        "title": e.title,
        "start_date": e.start_date.isoformat(),
        "end_date": e.end_date.isoformat(),
        "location": e.location,
        "description": e.description,
        "user_id": e.user_id
    } for e in events])

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

@calendar_bp.route('/local', methods=['POST'])
def add_local_event():
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
    return jsonify({"message": "Local event added.", "id": event.id}), 201

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