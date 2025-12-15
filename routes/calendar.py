from flask import Blueprint, jsonify, request, session
from database.db import db
from models.accounts import Admin, SchirmersNotary, Client
from models.bookings import Booking
import os
import json
from datetime import datetime, timedelta

calendar_bp = Blueprint('calendar', __name__, template_folder='frontend/templates')

def get_default_user():
    """Get the first admin user"""
    return Admin.query.first()

def get_admin_calendar_user():
    """Get the specific admin (ID 1) for calendar operations"""
    return Admin.query.get(1)

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
    """Generate available time slots based on SchirmersNotary detailed availability settings"""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        
        company = SchirmersNotary.query.first()
        if not company:
            return []
        
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_name = day_names[date.weekday()]
        
        if company.available_days_json:
            try:
                detailed_availability = json.loads(company.available_days_json)
                
                if day_name not in detailed_availability:
                    return []
                
                day_schedule = detailed_availability[day_name]
                office_start = day_schedule.get("start")
                office_end = day_schedule.get("end")
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error parsing available_days_json: {e}, falling back to simple availability")
                office_start = company.office_start
                office_end = company.office_end
                available_days = company.available_days
                available_day_numbers = [int(d.strip()) for d in available_days.split(",") if d.strip()]
                
                if date.weekday() not in available_day_numbers:
                    return []
        else:
            office_start = company.office_start or "09:00"
            office_end = company.office_end or "17:00"
            available_days = company.available_days or "0,1,2,3,4"
            available_day_numbers = [int(d.strip()) for d in available_days.split(",") if d.strip()]
            
            if date.weekday() not in available_day_numbers:
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

