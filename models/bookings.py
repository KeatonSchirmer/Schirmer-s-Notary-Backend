from database.db import db

class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    urgency = db.Column(db.String(50))
    date = db.Column(db.Date)
    time = db.Column(db.Time)
    location = db.Column(db.String(255))
    notes = db.Column(db.Text)
    rating = db.Column(db.Integer)
    feedback = db.Column(db.Text)   
    finances = db.relationship('Finance', backref='booking', lazy=True)
    mileage = db.relationship('Mileage', backref='booking', lazy=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=True)
    status = db.Column(db.Enum("pending", "accepted", "denied", "completed", name="booking_status"), default="pending")

    