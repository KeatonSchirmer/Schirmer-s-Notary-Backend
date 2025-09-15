from flask import Blueprint, request, jsonify
from models.mileage import Mileage
from database.db import db
from datetime import datetime, timedelta

mileage_bp = Blueprint('mileage', __name__)


@mileage_bp.route('/add', methods=['POST'])
def add_mileage():
    user_id = request.headers.get("X-User-Id")
    data = request.get_json()
    try:
        if not user_id:
            return jsonify({"error": "Not logged in"}), 401
        mileage = Mileage(
            user_id=user_id,
            miles=data.get('miles'),
            purpose=data.get('purpose'),
            date=datetime.strptime(data.get('date'), "%Y-%m-%d") if data.get('date') else datetime.utcnow(),
            time=data.get('time')
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
    user_id = request.headers.get("X-User-Id")
    try:
        if not user_id:
            return jsonify({"error": "Not logged in"}), 401
        entries = Mileage.query.filter_by(user_id=user_id).order_by(Mileage.date.desc()).all()
        return jsonify({
            "entries": [
                {
                    "id": m.id,
                    "date": m.date.strftime("%Y-%m-%d"),
                    "time": m.time,
                    "miles": m.miles,
                    "purpose": m.purpose,
                }
                for m in entries
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@mileage_bp.route('/weekly', methods=['GET'])
def get_weekly_mileage():
    user_id = request.headers.get("X-User-Id")
    try:
        if not user_id:
            return jsonify({"error": "Not logged in"}), 401
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        entries = Mileage.query.filter(
            Mileage.user_id == user_id,
            Mileage.date >= week_start
        ).all()
        total = sum(m.miles for m in entries)
        return jsonify({"weekly_mileage": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@mileage_bp.route('/<int:mileage_id>', methods=['PATCH', 'PUT'])
def edit_mileage(mileage_id):
    user_id = request.headers.get("X-User-Id")
    data = request.get_json()
    mileage = Mileage.query.filter_by(id=mileage_id, user_id=user_id).first()
    if not mileage:
        return jsonify({"error": "Mileage entry not found"}), 404

    # Update fields if provided
    if 'purpose' in data:
        mileage.purpose = data['purpose']
    if 'notes' in data:
        mileage.notes = data['notes']  # If you have a notes field
    db.session.commit()
    return jsonify({"message": "Mileage entry updated."})

@mileage_bp.route('/<int:mileage_id>', methods=['DELETE'])
def delete_mileage(mileage_id):
    user_id = request.headers.get("X-User-Id")
    mileage = Mileage.query.filter_by(id=mileage_id, user_id=user_id).first()
    if not mileage:
        return jsonify({"error": "Mileage entry not found"}), 404

    db.session.delete(mileage)
    db.session.commit()
    return jsonify({"message": "Mileage entry deleted."})    