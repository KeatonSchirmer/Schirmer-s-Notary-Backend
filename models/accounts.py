from datetime import datetime
from database.db import db

class Admin(db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(255))
    license_number = db.Column(db.String(100))
    license_expiration = db.Column(db.Date)
    password_hash = db.Column(db.String(255), nullable=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_code = db.Column(db.String(12))
    two_factor_code_created = db.Column(db.DateTime)
    notification_enabled = db.Column(db.Boolean, default=True)
    push_token = db.Column(db.String(255))
    google_access_token = db.Column(db.Text)
    google_refresh_token = db.Column(db.Text) 
    google_token_expires = db.Column(db.DateTime)
    google_calendar_connected = db.Column(db.Boolean, default=False)
    
    employment_type = db.Column(db.Enum("full_time", "part_time", name="employment_type"), default="full_time")
    salary = db.Column(db.Numeric(10, 2), default=0.0)
    hourly_rate = db.Column(db.Numeric(8, 2), default=0.0)
    hours_per_week = db.Column(db.Integer, default=40)
    pay_period_start = db.Column(db.String(10))
    pay_period_end = db.Column(db.String(10))
    availability = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    account_status = db.Column(db.Enum("pending", "confirmed", "suspended", name="account_status"), default="pending")


    def __repr__(self):
        return f"<Admin {self.email}>"

class Company(db.Model):
    __tablename__ = "company"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    address = db.Column(db.String(255))
    contact_points = db.relationship('Client', back_populates='company', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address
        }

    def __repr__(self):
        return f"<Company {self.name}>"

class Client(db.Model):
    __tablename__ = "client"

    id = db.Column(db.Integer, primary_key=True)
    square_customer_id = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_code = db.Column(db.String(12))
    two_factor_code_created = db.Column(db.DateTime)
    premium = db.Column(db.Enum("None", "Business", "Premium", "Corporate", "Custom", name="premium_tier"), default="None")
    push_token = db.Column(db.String(255))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True, index=True)
    company = db.relationship('Company', back_populates='contact_points')
    bookings = db.relationship('Booking', backref='client', lazy=True)
    billing = db.relationship('Billing', uselist=False, backref='client')
    google_access_token = db.Column(db.Text)
    google_refresh_token = db.Column(db.Text) 
    google_token_expires = db.Column(db.DateTime)
    google_calendar_connected = db.Column(db.Boolean, default=False)


    def __repr__(self):
        return f"<Client {self.email}>"

class SchirmersNotary(db.Model):
    __tablename__ = "schirmersnotary"

    id = db.Column(db.Integer, primary_key=True)
    ceo_admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True)
    office_start = db.Column(db.String(5))
    office_end = db.Column(db.String(5))
    available_days = db.Column(db.String(50))
    available_days_json = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<SchirmersNotary {self.address}>"