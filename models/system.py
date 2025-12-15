from database.db import db
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
import datetime

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False)

class Backup(db.Model):
    __tablename__ = 'backups'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    size = db.Column(db.String(20))
    created_at = db.Column(db.String(30))
    type = db.Column(db.String(20))
 
class Service(db.Model):
    __tablename__ = "services"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "active": self.active
        }

class Subscription(db.Model):
    __tablename__ = "subscription"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percentage = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "discount_percentage": self.discount_percentage,
            "active": self.active
        }

class PricingPolicy(db.Model):
    __tablename__ = 'pricing_policy'
    
    id = db.Column(db.Integer, primary_key=True)
    base_notary_fee = db.Column(db.Numeric(10, 2), default=30.00)
    base_travel_fee = db.Column(db.Numeric(10, 2), default=20.00)
    free_travel_miles = db.Column(db.Integer, default=15)
    additional_mile_rate = db.Column(db.Numeric(10, 2), default=1.00)
    additional_signer_fee = db.Column(db.Numeric(10, 2), default=10.00)
    rush_fee_same_day = db.Column(db.Numeric(10, 2), default=15.00)
    rush_fee_emergency = db.Column(db.Numeric(10, 2), default=25.00)
    rush_fee_holiday = db.Column(db.Numeric(10, 2), default=35.00)
    loan_signing_flat_rate = db.Column(db.Numeric(10, 2), default=150.00)
    loan_signing_rush_fee = db.Column(db.Numeric(10, 2), default=25.00)
    ron_base_fee = db.Column(db.Numeric(10, 2), default=30.00)
    ron_rush_fee = db.Column(db.Numeric(10, 2), default=15.00)
    document_printing_per_page = db.Column(db.Numeric(10, 2), default=2.00)
    document_scanning_fee = db.Column(db.Numeric(10, 2), default=5.00)
    waiting_time_fee = db.Column(db.Numeric(10, 2), default=10.00)
    cancellation_fee = db.Column(db.Numeric(10, 2), default=25.00)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "base_notary_fee": float(self.base_notary_fee),
            "base_travel_fee": float(self.base_travel_fee),
            "free_travel_miles": self.free_travel_miles,
            "additional_mile_rate": float(self.additional_mile_rate),
            "additional_signer_fee": float(self.additional_signer_fee),
            "rush_fee_same_day": float(self.rush_fee_same_day),
            "rush_fee_emergency": float(self.rush_fee_emergency),
            "rush_fee_holiday": float(self.rush_fee_holiday),
            "loan_signing_flat_rate": float(self.loan_signing_flat_rate),
            "loan_signing_rush_fee": float(self.loan_signing_rush_fee),
            "ron_base_fee": float(self.ron_base_fee),
            "ron_rush_fee": float(self.ron_rush_fee),
            "document_printing_per_page": float(self.document_printing_per_page),
            "document_scanning_fee": float(self.document_scanning_fee),
            "waiting_time_fee": float(self.waiting_time_fee),
            "cancellation_fee": float(self.cancellation_fee),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }