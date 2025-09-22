from datetime import datetime
from database.db import db

class JournalSigner(db.Model):
    __tablename__ = "journal_signer"
    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(20))

class JournalEntry(db.Model):
    __tablename__ = "journal"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(255))
    document_type = db.Column(db.String(100), nullable=False)
    id_verification = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    signers = db.relationship('JournalSigner', backref='journal', lazy=True)
    completed_bookings = db.relationship('Booking', backref='journal_entry', lazy=True)
    pdfs = db.relationship('PDF', backref='journal_entry', lazy=True)

class PDF(db.Model):
    __tablename__ = "pdfs"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=False)
    finance_id = db.Column(db.Integer, db.ForeignKey('finances.id'), nullable=True)