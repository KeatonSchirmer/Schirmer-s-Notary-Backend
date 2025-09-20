from datetime import datetime
from sqlalchemy import Numeric, Enum
from database.db import db

class Finance(db.Model):
    __tablename__ = "finances"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(Enum("profit", "expense", name="finance_type"), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))
    pdfs = db.relationship('PDF', backref='finance', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "amount": float(self.amount) if self.amount is not None else None,
            "date": self.date.strftime("%Y-%m-%d") if self.date else "",
            "booking_id": self.booking_id
        }

class Mileage(db.Model):
    __tablename__ = "mileage"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    time = db.Column(db.String(10))
    notes = db.Column(db.Text)
    job_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.strftime("%Y-%m-%d") if self.date else "",
            "distance": self.distance,
            "time": self.time,
            "notes": self.notes,
            "job_id": self.job_id
        }
    
    