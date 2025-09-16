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


class Mileage(db.Model):
    __tablename__ = "mileage"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    time = db.Column(db.String(10))
    notes = db.Column(db.Text)
    job_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))

    