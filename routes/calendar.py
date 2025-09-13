from flask import Blueprint, jsonify
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
    # You can filter/format events as needed
    return jsonify({"events": events})

@calendar_bp.route('/local', methods=['GET'])
def get_local_events():
    events = AcceptedJob.query.all()
    events_list = []
    for e in events:
        if e.service_date:
            events_list.append({
                "id": e.id,
                "name": e.name,
                "start_date": e.service_date.isoformat(),
                "location": e.location,
            })
    return jsonify({"events": events_list})

