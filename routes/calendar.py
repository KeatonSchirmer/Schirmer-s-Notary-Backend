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

    event = Event(
        title=event_data['title'],
        start_date=event_data['start_date'],
        end_date=event_data['end_date'],
        description=event_data['description'],
        location=event_data['location'],
        user_id=event_data['user_id'],
    )
    db.session.add(event)
    db.session.commit()

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

