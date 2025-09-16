from datetime import datetime
from database.db import db

class Admin(db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(255))
    license_number = db.Column(db.String(100))
    license_expiration = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_code = db.Column(db.String(12))
    two_factor_code_created = db.Column(db.DateTime)
    notification_enabled = db.Column(db.Boolean, default=True)

class Client(db.Model):
    __tablename__ = "client"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_code = db.Column(db.String(12))
    two_factor_code_created = db.Column(db.DateTime)
    premium = db.Column(db.Enum("None", "Business", "Premium", "Corporate", "Custom", name="premium_tier"), default="None")
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    bookings = db.relationship('Booking', backref='client', lazy=True)

class Company(db.Model):
    __tablename__ = "company"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    contact_points = db.relationship('Client', backref='company', lazy=True)

class SchirmersNotary(db.Model):
    __tablename__ = "schirmersnotary"

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255))
    office_start = db.Column(db.String(5))
    office_end = db.Column(db.String(5))
    available_days = db.Column(db.String(50))