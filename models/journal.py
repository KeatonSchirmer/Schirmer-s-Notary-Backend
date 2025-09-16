from datetime import datetime
from database.db import db

class JournalEntry(db.Model):
    __tablename__ = "journal"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(255))
    signer_name = db.Column(db.String(120), nullable=False)
    signer_address = db.Column(db.String(255))
    signer_phone = db.Column(db.String(20))
    document_type = db.Column(db.String(100), nullable=False)
    id_verification = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    completed_bookings = db.relationship('Booking', backref='journal_entry', lazy=True)
    pdfs = db.relationship('PDF', backref='journal_entry', lazy=True)

class PDF(db.Model):
    __tablename__ = "pdfs"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    journal = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=False)
    finance = db.Column(db.Integer, db.ForeignKey('finances.id'), nullable=True)