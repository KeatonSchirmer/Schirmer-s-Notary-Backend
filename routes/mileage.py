from flask import Blueprint, request, jsonify
from models.business import Mileage
from database.db import db
from datetime import datetime, timedelta

mileage_bp = Blueprint('mileage', __name__)

@mileage_bp.route('/add', methods=['POST'])
def add_mileage():
    data = request.get_json()
    try:
        mileage = Mileage(
            date=datetime.strptime(data.get('date'), "%Y-%m-%d") if data.get('date') else datetime.utcnow(),
            distance=data.get('distance'),
            time=data.get('time'),
            notes=data.get('notes')
        )
        db.session.add(mileage)
        db.session.commit()
        db.session.refresh(mileage)
        return jsonify({"message": "Mileage entry added", "id": mileage.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@mileage_bp.route('/', methods=['GET'])
def get_mileage():
    try:
        entries = Mileage.query.order_by(Mileage.date.desc()).all()
        return jsonify({
            "entries": [
                {
                    "id": m.id,
                    "date": m.date.strftime("%Y-%m-%d"),
                    "time": m.time,
                    "distance": m.distance,
                    "notes": m.notes,
                }
                for m in entries
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@mileage_bp.route('/weekly', methods=['GET'])
def get_weekly_mileage():
    try:
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        entries = Mileage.query.filter(
            Mileage.date >= week_start
        ).all()
        total = sum(m.distance for m in entries)
        return jsonify({"weekly_mileage": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@mileage_bp.route('/<int:mileage_id>', methods=['PATCH', 'PUT'])
def edit_mileage(mileage_id):
    data = request.get_json()
    mileage = Mileage.query.get(mileage_id)
    if not mileage:
        return jsonify({"error": "Mileage entry not found"}), 404

    # Update fields if provided
    if 'distance' in data:
        mileage.distance = data['distance']
    if 'time' in data:
        mileage.time = data['time']
    if 'job_id' in data:
        mileage.job_id = data['job_id']    
    if 'notes' in data:
        mileage.notes = data['notes']
    if 'date' in data:
        try:
            mileage.date = datetime.strptime(data['date'], "%Y-%m-%d")
        except Exception:
            pass
    db.session.commit()
    return jsonify({"message": "Mileage entry updated."})

@mileage_bp.route('/<int:mileage_id>', methods=['DELETE'])
def delete_mileage(mileage_id):
    mileage = Mileage.query.get(mileage_id)
    if not mileage:
        return jsonify({"error": "Mileage entry not found"}), 404

    db.session.delete(mileage)
    db.session.commit()
    return jsonify({"message": "Mileage entry deleted."})