from . import db

class PendingBooking(db.Model):
    __tablename__ = "pending"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    urgency = db.Column(db.String(50))
    date = db.Column(db.Date)
    time = db.Column(db.String(8))
    notes = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)


class AcceptedBooking(db.Model):
    __tablename__ = "accepted"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    urgency = db.Column(db.String(50))
    date = db.Column(db.Date)
    time = db.Column(db.String(8))
    location = db.Column(db.String(255))
    notes = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)


class DeniedBooking(db.Model):
    __tablename__ = "denied"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    service = db.Column(db.String(100))
    date = db.Column(db.Date)
    notes = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

class CompletedBooking(db.Model):
    __tablename__ = "completed"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date)
    time = db.Column(db.String(8))
    location = db.Column(db.String(255))
    notes = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=True)
    mileage_id = db.Column(db.Integer, db.ForeignKey('mileage.id'), nullable=True)