from flask import Blueprint, request, jsonify
from database.db import db
from datetime import datetime
from models.business import Finance

finances_bp = Blueprint('finances', __name__)

@finances_bp.route('/', methods=['GET'])
def get_finances():
    entries = Finance.query.order_by(Finance.date.desc()).all()
    return jsonify([entry.to_dict() for entry in entries])

@finances_bp.route('/add', methods=['POST'])
def add_finance():
    data = request.get_json()
    entry = Finance(
        type=data["type"],
        description=data.get("description", ""),
        amount=data["amount"],
        date=datetime.strptime(data["date"], "%Y-%m-%d")
    )
    db.session.add(entry)
    db.session.commit()
    db.session.refresh(entry)
    return jsonify(entry.to_dict())

@finances_bp.route('/<int:finance_id>', methods=['PUT'])
def update_finance(finance_id):
    data = request.get_json()
    entry = Finance.query.get(finance_id)
    if not entry:
        return jsonify({"error": "Finance entry not found"}), 404
    entry.type = data.get("type", entry.type)
    entry.description = data.get("description", entry.description)
    entry.amount = data.get("amount", entry.amount)
    if "date" in data:
        entry.date = datetime.strptime(data["date"], "%Y-%m-%d")
    db.session.commit()
    db.session.refresh(entry)
    return jsonify(entry.to_dict())

@finances_bp.route('/<int:finance_id>', methods=['DELETE'])
def delete_finance(finance_id):
    entry = Finance.query.get(finance_id)
    if not entry:
        return jsonify({"error": "Finance entry not found"}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Deleted"})

