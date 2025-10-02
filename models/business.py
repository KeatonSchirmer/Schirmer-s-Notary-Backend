from datetime import datetime
from sqlalchemy import Numeric, Enum
from database.db import db
from utils.encrypt import encryption_manager

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
    
class Billing(db.Model):
    __tablename__ = "billing"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    _tax_id = db.Column('tax_id', db.Text)  # Encrypted
    payment_method = db.Column(db.String(50))
    _card_number = db.Column('card_number', db.Text)  # Encrypted
    card_expir = db.Column(db.String(5))
    _card_cvv = db.Column('card_cvv', db.Text)  # Encrypted

    @property
    def tax_id(self):
        """Decrypt tax ID when accessed"""
        return encryption_manager.decrypt(self._tax_id)
    
    @tax_id.setter
    def tax_id(self, value):
        """Encrypt tax ID when set"""
        self._tax_id = encryption_manager.encrypt(value) if value else None

    @property
    def card_number(self):
        """Decrypt card number when accessed"""
        return encryption_manager.decrypt(self._card_number)
    
    @card_number.setter
    def card_number(self, value):
        """Encrypt card number when set"""
        self._card_number = encryption_manager.encrypt(value) if value else None

    @property
    def card_cvv(self):
        """Decrypt CVV when accessed"""
        return encryption_manager.decrypt(self._card_cvv)
    
    @card_cvv.setter
    def card_cvv(self, value):
        """Encrypt CVV when set"""
        self._card_cvv = encryption_manager.encrypt(value) if value else None

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
            "tax_id": "***" if self._tax_id else None,  # Never expose real tax_id
            "payment_method": self.payment_method,
            "card_expir": self.card_expir,
            "card_cvv": "***" if self._card_cvv else None,  # Never expose real CVV
            "card_number": self.card_number[-4:] if self.card_number else None  # Only last 4 digits
        }
    
class DirectDeposit(db.Model):
    __tablename__ = "direct_deposits"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))
    bank_name = db.Column(db.String(100))
    account_type = db.Column(Enum("checking", "savings", name="account_type"), nullable=False)
    _account_number = db.Column('account_number', db.Text)  # Encrypted
    _routing_number = db.Column('routing_number', db.Text)  # Encrypted

    @property
    def account_number(self):
        """Decrypt account number when accessed"""
        return encryption_manager.decrypt(self._account_number)
    
    @account_number.setter
    def account_number(self, value):
        """Encrypt account number when set"""
        self._account_number = encryption_manager.encrypt(value) if value else None

    @property
    def routing_number(self):
        """Decrypt routing number when accessed"""
        return encryption_manager.decrypt(self._routing_number)
    
    @routing_number.setter
    def routing_number(self, value):
        """Encrypt routing number when set"""
        self._routing_number = encryption_manager.encrypt(value) if value else None

    def to_dict(self):
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "bank_name": self.bank_name,
            "account_type": self.account_type,
            "account_number": self.account_number[-4:] if self.account_number else None,  # Only last 4 digits
            "routing_number": "***" if self._routing_number else None  # Never expose real routing number
        }