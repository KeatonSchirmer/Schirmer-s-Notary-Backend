from flask import Blueprint, jsonify, request, session
from google.oauth2 import service_account
from googleapiclient.discovery import build
from database.db import db
from models.accounts import Admin, SchirmersNotary, Client
from models.bookings import Booking
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from datetime import datetime, timedelta

calendar_bp = Blueprint('calendar', __name__, template_folder='frontend/templates')

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')

def get_default_user():
    """Get the first admin user"""
    return Admin.query.first()

def get_admin_calendar_user():
    """Get the specific admin (ID 1) for calendar operations"""
    return Admin.query.get(1)

def get_calendar_service():
    """Get Google Calendar service using service account"""
    if not SERVICE_ACCOUNT_FILE:
        raise ValueError("Google service account file not configured")
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('calendar', 'v3', credentials=credentials)

def get_user_calendar_service(user):
    """Get calendar service using user's OAuth tokens"""
    if not hasattr(user, 'google_calendar_connected') or not user.google_calendar_connected:
        return None
        
    try:
        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
            scopes=SCOPES
        )
        
        if credentials.expired:
            credentials.refresh(Request())
            user.google_access_token = credentials.token
            user.google_token_expires = credentials.expiry
            db.session.commit()
            
        service = build('calendar', 'v3', credentials=credentials)
        return service
        
    except Exception as e:
        print(f"Failed to get user calendar service: {e}")
        return None

def get_user_busy_times(user, date_str):
    """Get busy times from user's primary calendar"""
    service = get_user_calendar_service(user)
    if not service:
        return []
        
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        time_min = date.strftime("%Y-%m-%dT00:00:00Z")
        time_max = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        busy_times = []
        events = events_result.get('items', [])
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            if 'T' in start:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                busy_times.append((start_dt, end_dt))
                
        return busy_times
        
    except Exception as e:
        print(f"Error getting user busy times: {e}")
        return []

def get_local_busy_times(date_str):
    """Get busy times from local bookings for a specific date"""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        bookings = Booking.query.filter_by(date=date, status="accepted").all()
        
        busy_times = []
        for booking in bookings:
            if booking.time:
                start_dt = datetime.combine(booking.date, booking.time)
                end_dt = start_dt + timedelta(hours=1)
                busy_times.append((start_dt, end_dt))
                
        return busy_times
        
    except Exception as e:
        print(f"Error getting local busy times: {e}")
        return []

def generate_available_slots(date_str, busy_times):
    """Generate available time slots based on SchirmersNotary availability settings"""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        
        company = SchirmersNotary.query.first()
        if not company:
            return []
        
        office_start = company.office_start or "09:00"
        office_end = company.office_end or "17:00"
        available_days = company.available_days or "0,1,2,3,4" 
        day_of_week = date.weekday() 
        available_day_numbers = [int(d.strip()) for d in available_days.split(",") if d.strip()]
        
        if day_of_week not in available_day_numbers:
            return [] 
        
        try:
            start_hour, start_min = map(int, office_start.split(":"))
            end_hour, end_min = map(int, office_end.split(":"))
        except (ValueError, AttributeError):
            start_hour, start_min = 9, 0
            end_hour, end_min = 17, 0
        
        office_start_dt = date.replace(hour=start_hour, minute=start_min)
        office_end_dt = date.replace(hour=end_hour, minute=end_min)
        
        available_slots = []
        current_slot = office_start_dt
        
        while current_slot + timedelta(minutes=30) <= office_end_dt:
            slot_end = current_slot + timedelta(minutes=30)
            
            is_busy = False
            for busy_start, busy_end in busy_times:
                if hasattr(busy_start, 'tzinfo') and busy_start.tzinfo:
                    busy_start = busy_start.replace(tzinfo=None)
                if hasattr(busy_end, 'tzinfo') and busy_end.tzinfo:
                    busy_end = busy_end.replace(tzinfo=None)
                    
                if (current_slot < busy_end and slot_end > busy_start):
                    is_busy = True
                    break
            
            now = datetime.now()
            is_past = False
            if date.date() == now.date() and current_slot <= now:
                is_past = True
            
            if not is_busy and not is_past:
                available_slots.append({
                    "start_time": current_slot.strftime("%H:%M"),
                    "end_time": slot_end.strftime("%H:%M"),
                    "datetime": current_slot.isoformat(),
                    "date": date_str,
                    "available": True
                })
            
            current_slot += timedelta(minutes=30)
        
        return available_slots
        
    except Exception as e:
        print(f"Error generating available slots: {e}")
        return []

#! Will be updated later to handle employee availability

#def generate_available_slots(date_str, busy_times):
#    """Generate available time slots for a given date, excluding busy times"""
#    try:
#        date = datetime.strptime(date_str, "%Y-%m-%d")
#        
#        company = SchirmersNotary.query.first()
#        if not company:
#            office_start = "09:00"
#            office_end = "17:00"
#            available_days = "0,1,2,3,4"
#        else:
#            office_start = company.office_start or "09:00"
#            office_end = company.office_end or "17:00"
#            available_days = company.available_days or "0,1,2,3,4"
#        
#        day_of_week = date.weekday()
#        available_day_numbers = [int(d) for d in available_days.split(",") if d.strip()]
#        
#        if day_of_week not in available_day_numbers:
#            return []  
#        
#        start_hour, start_min = map(int, office_start.split(":"))
#        end_hour, end_min = map(int, office_end.split(":"))
#        
#        office_start_dt = date.replace(hour=start_hour, minute=start_min)
#        office_end_dt = date.replace(hour=end_hour, minute=end_min)
#        
#        available_slots = []
#        current_slot = office_start_dt
#        
#        while current_slot + timedelta(minutes=45) <= office_end_dt:
#            slot_end = current_slot + timedelta(minutes=30)
#            
#            # Check if this slot conflicts with any busy time
#            is_busy = False
#            for busy_start, busy_end in busy_times:
#                if (current_slot < busy_end and slot_end > busy_start):
#                    is_busy = True
#                    break
#            
#            if not is_busy:
#                available_slots.append({
#                    "start_time": current_slot.strftime("%H:%M"),
#                    "end_time": slot_end.strftime("%H:%M"),
#                    "datetime": current_slot.isoformat()
#                })
#            
#            current_slot += timedelta(minutes=30)
#        
#        return available_slots
#        
#    except Exception as e:
#        print(f"Error generating available slots: {e}")
#        return []

def add_event_to_calendar(booking):
    """Add booking to Google Calendar using service account"""
    if not SERVICE_ACCOUNT_FILE or not CALENDAR_ID:
        print("Google Calendar credentials not configured")
        return

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)

        event = {
            'summary': booking.service,
            'description': booking.notes,
            'start': {
                'dateTime': f"{booking.date.strftime('%Y-%m-%d')}T{booking.time.strftime('%H:%M:%S')}",
                'timeZone': 'America/Chicago',
            },
            'end': {
                'dateTime': (datetime.combine(booking.date, booking.time) + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'America/Chicago',
            },
        }

        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"Event added to Google Calendar: {booking.service}")
        
    except Exception as e:
        print(f"Failed to add event to calendar: {e}")

#! Will be updated later to handle employee availability

#@calendar_bp.route('/slots', methods=['GET'])
#def get_available_slots():
#    """Get available slots based on admin calendar (ID 1) and local bookings"""
#    try:
#        date_str = request.args.get('date')
#        if not date_str:
#            return jsonify({"error": "Date parameter required"}), 400
#        
#        admin = get_admin_calendar_user()
#        if not admin:
#            return jsonify({"error": "Admin user (ID 1) not found"}), 404
#        
#        busy_times = []
#        
#        if hasattr(admin, 'google_calendar_connected') and admin.google_calendar_connected:
#            busy_times += get_user_busy_times(admin, date_str)
#        
#        busy_times += get_local_busy_times(date_str)
#        
#        available_slots = generate_available_slots(date_str, busy_times)
#        
#        # Format slots to match frontend expectations
#        formatted_slots = []
#        for slot in available_slots:
#            formatted_slots.append({
#                "date": date_str,
#                "time": slot["start_time"],
#                "available": True
#            })
#        
#        return jsonify({
#            "date": date_str,
#            "slots": formatted_slots,  # Changed from available_slots
#            "admin_calendar_connected": getattr(admin, 'google_calendar_connected', False),
#            "total_slots": len(formatted_slots)
#        }), 200
#        
#    except Exception as e:
#        print(f"Error getting available slots: {e}")
#        return jsonify({"error": "Failed to get available slots"}), 500

#! The below is temporary

@calendar_bp.route('/slots', methods=['GET'])
def get_available_slots():
    """Get available slots based on SchirmersNotary availability and local bookings"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({"error": "Date parameter required"}), 400
        
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        company = SchirmersNotary.query.first()
        if not company:
            return jsonify({
                "date": date_str,
                "slots": [],
                "error": "No availability configured. Please set business hours first.",
                "total_slots": 0
            }), 200
        
        busy_times = get_local_busy_times(date_str)
        
        available_slots = generate_available_slots(date_str, busy_times)
        
        formatted_slots = []
        for slot in available_slots:
            formatted_slots.append({
                "date": date_str,
                "time": slot["start_time"],
                "end_time": slot["end_time"],
                "datetime": slot["datetime"],
                "available": True
            })
        
        return jsonify({
            "date": date_str,
            "slots": formatted_slots,
            "availability_source": "schirmers_notary_table",
            "business_hours": f"{company.office_start} - {company.office_end}",
            "available_days": company.available_days,
            "total_slots": len(formatted_slots)
        }), 200
        
    except Exception as e:
        print(f"Error getting available slots: {e}")
        return jsonify({"error": f"Failed to get available slots: {str(e)}"}), 500

@calendar_bp.route('/availability/status', methods=['GET'])
def get_availability_status():
    """Check if availability is properly configured"""
    try:
        company = SchirmersNotary.query.first()
        
        if not company:
            return jsonify({
                "configured": False,
                "message": "No availability settings found. Please configure business hours.",
                "default_setup_needed": True
            }), 200
        
        return jsonify({
            "configured": True,
            "office_start": company.office_start,
            "office_end": company.office_end,
            "available_days": company.available_days,
            "available_days_list": company.available_days.split(",") if company.available_days else [],
            "message": "Availability is configured"
        }), 200
        
    except Exception as e:
        print(f"Error checking availability status: {e}")
        return jsonify({"error": "Failed to check availability status"}), 500

@calendar_bp.route('/availability/quick-setup', methods=['POST'])
def quick_setup_availability():
    """Quick setup for default business hours"""
    try:
        data = request.get_json() or {}
        
        company = SchirmersNotary.query.first()
        if not company:
            company = SchirmersNotary()
        
        company.office_start = data.get("office_start", "09:00")
        company.office_end = data.get("office_end", "17:00")
        company.available_days = data.get("available_days", "0,1,2,3,4") 
        company.address = data.get("address", company.address or "")
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify({
            "message": "Availability configured successfully",
            "office_start": company.office_start,
            "office_end": company.office_end,
            "available_days": company.available_days,
            "setup_complete": True
        }), 200
        
    except Exception as e:
        print(f"Error setting up availability: {e}")
        return jsonify({"error": "Failed to setup availability"}), 500

#! The above is temporary

@calendar_bp.route('/admin/calendar-status', methods=['GET'])
def get_admin_calendar_status():
    """Check if admin (ID 1) has Google Calendar connected"""
    admin = get_admin_calendar_user()
    if not admin:
        return jsonify({"error": "Admin user (ID 1) not found"}), 404
    
    return jsonify({
        "admin_id": admin.id,
        "admin_name": admin.name,
        "google_calendar_connected": getattr(admin, 'google_calendar_connected', False),
        "calendar_access_token_exists": bool(getattr(admin, 'google_access_token', None))
    }), 200

@calendar_bp.route('/local', methods=['GET'])
def get_local_events():
    """Get all accepted local bookings"""
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
    """Add a new local booking event"""
    data = request.get_json()
    user = get_default_user()
    if not user:
        return jsonify({"error": "No admin user found"}), 404

    try:
        date_str = data.get('date')
        time_str = data.get('time')

        if date_str and 'T' in date_str:
            date_part, time_part = date_str.split('T')
            date_str = date_part
            time_str = time_part

        booking = Booking(
            client_id=data.get('client_id'),
            service=data.get('service'),
            urgency=data.get('urgency', 'normal'),
            date=datetime.strptime(date_str, "%Y-%m-%d"),
            time=datetime.strptime(time_str, "%H:%M").time() if time_str else None,
            location=data.get('location'),
            notes=data.get('notes'),
            status="accepted"
        )
        db.session.add(booking)
        db.session.commit()

        add_event_to_calendar(booking)

        return jsonify({"message": "Booking added successfully", "id": booking.id}), 201
        
    except Exception as e:
        print(f"Error adding local event: {e}")
        return jsonify({"error": "Failed to add booking"}), 500

@calendar_bp.route('/local/<int:booking_id>', methods=['PUT'])
def edit_local_event(booking_id):
    """Edit an existing local booking"""
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
        
    try:
        data = request.get_json()
        booking.service = data.get('service', booking.service)
        booking.date = datetime.strptime(data.get('date'), "%Y-%m-%d") if data.get('date') else booking.date
        booking.time = datetime.strptime(data.get('time'), "%H:%M").time() if data.get('time') else booking.time
        booking.location = data.get('location', booking.location)
        booking.notes = data.get('notes', booking.notes)
        booking.client_id = data.get('client_id', booking.client_id)
        
        db.session.commit()
        return jsonify({"message": "Booking updated successfully"})
        
    except Exception as e:
        print(f"Error updating booking: {e}")
        return jsonify({"error": "Failed to update booking"}), 500

@calendar_bp.route('/local/<int:booking_id>', methods=['DELETE'])
def delete_local_event(booking_id):
    """Delete a local booking"""
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
        
    try:
        db.session.delete(booking)
        db.session.commit()
        return jsonify({"message": "Booking deleted successfully"})
        
    except Exception as e:
        print(f"Error deleting booking: {e}")
        return jsonify({"error": "Failed to delete booking"}), 500

@calendar_bp.route('/availability', methods=['GET'])
def get_company_availability():
    """Get company availability settings"""
    company = SchirmersNotary.query.first()
    if not company:
        return jsonify({"error": "No company settings found"}), 404
        
    return jsonify({
        "address": company.address,
        "office_start": company.office_start,
        "office_end": company.office_end,
        "available_days": company.available_days.split(",") if company.available_days else [],
        "available_days_json": company.available_days_json or "{}"
    })

@calendar_bp.route('/availability', methods=['POST'])
def set_company_availability():
    """Set company availability settings"""
    try:
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
            
        if "available_days_json" in data:
            company.available_days_json = data["available_days_json"]
            
        db.session.add(company)
        db.session.commit()
        
        return jsonify({"message": "Company availability saved successfully"}), 200
        
    except Exception as e:
        print(f"Error saving availability: {e}")
        return jsonify({"error": "Failed to save availability"}), 500

@calendar_bp.route('/sync/local-to-google', methods=['POST'])
def sync_local_to_google():
    """Sync all accepted local bookings to Google Calendar"""
    try:
        bookings = Booking.query.filter_by(status="accepted").all()
        synced = []
        
        for booking in bookings:
            add_event_to_calendar(booking)
            synced.append(booking.id)
            
        return jsonify({
            "message": f"Synced {len(synced)} bookings to Google Calendar",
            "synced_ids": synced
        }), 200
        
    except Exception as e:
        print(f"Error syncing to Google: {e}")
        return jsonify({"error": "Failed to sync to Google Calendar"}), 500

@calendar_bp.route('/google-sync-to-local', methods=['GET', 'POST'])
def sync_google_to_local():
    """Legacy endpoint - sync Google Calendar events to local bookings"""
    print("Starting Google Calendar sync...")
    try:
        if not SERVICE_ACCOUNT_FILE or not CALENDAR_ID:
            return jsonify({"error": "Google Calendar not configured"}), 500
            
        service = get_calendar_service()
        time_min = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        
        admin = get_default_user()
        if admin:
            client = Client.query.filter_by(email=admin.email).first()
            if not client:
                client = Client(name=admin.name, email=admin.email)
                db.session.add(client)
                db.session.commit()
            admin_client_id = client.id
        else:
            return jsonify({"error": "No admin user found"}), 404

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        synced = []
        
        for event in events:
            summary = event.get('summary', 'No Title')
            notes = event.get('description', '')
            start = event['start'].get('dateTime') or event['start'].get('date')
            
            if start:
                if 'T' not in start:
                    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
                    existing = Booking.query.filter_by(date=start_dt, service=summary).first()
                    if not existing:
                        booking = Booking(
                            client_id=admin_client_id,
                            service=summary,
                            date=start_dt,
                            time=datetime.min.time(),
                            notes=notes,
                            status="accepted"
                        )
                        db.session.add(booking)
                        synced.append(summary)
                else: 
                    start_dt = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
                    existing = Booking.query.filter_by(
                        date=start_dt.date(), 
                        time=start_dt.time(), 
                        service=summary
                    ).first()
                    if not existing:
                        booking = Booking(
                            client_id=admin_client_id,
                            service=summary,
                            date=start_dt.date(),
                            time=start_dt.time(),
                            notes=notes,
                            status="accepted"
                        )
                        db.session.add(booking)
                        synced.append(summary)
        
        db.session.commit()
        return jsonify({
            "message": f"Synced {len(synced)} Google events to local calendar",
            "synced_events": synced
        }), 200
        
    except Exception as e:
        print(f"Error syncing Google Calendar: {e}")
        return jsonify({"error": str(e)}), 500

@calendar_bp.route('/all', methods=['GET'])
def get_all_events():
    """Get all events from both local and Google Calendar"""
    try:
        local_events = Booking.query.filter_by(status="accepted").all()
        local = [{
            "id": b.id,
            "name": b.service,
            "start_date": f"{b.date.strftime('%Y-%m-%d')}T{b.time.strftime('%H:%M')}" if b.time else b.date.strftime('%Y-%m-%d'),
            "location": b.location,
            "notes": b.notes,
            "source": "local"
        } for b in local_events]

        google_events = []
        if SERVICE_ACCOUNT_FILE and CALENDAR_ID:
            try:
                service = get_calendar_service()
                time_min = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
                events_result = service.events().list(
                    calendarId=CALENDAR_ID,
                    timeMin=time_min,
                    maxResults=50,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                for event in events_result.get('items', []):
                    summary = event.get('summary', 'No Title')
                    notes = event.get('description', '')
                    location = event.get('location', '')
                    start = event['start'].get('dateTime') or event['start'].get('date')
                    
                    if start:
                        if 'T' not in start:
                            google_events.append({
                                "id": event['id'],
                                "name": summary,
                                "start_date": start,
                                "location": location,
                                "notes": notes,
                                "source": "google"
                            })
                        else:
                            start_dt = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
                            google_events.append({
                                "id": event['id'],
                                "name": summary,
                                "start_date": start_dt.strftime("%Y-%m-%dT%H:%M"),
                                "location": location,
                                "notes": notes,
                                "source": "google"
                            })
            except Exception as e:
                print(f"Error getting Google events: {e}")

        all_events = local + google_events
        return jsonify({"events": all_events}), 200
        
    except Exception as e:
        print(f"Error getting all events: {e}")
        return jsonify({"error": "Failed to get events"}), 500