from database.db import db

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)
    id_type = db.Column(db.String(50), nullable=True)
    id_number = db.Column(db.String(50), nullable=True)
    signature = db.Column(db.String(255), nullable=True)  # Path to signature image or text
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'client_name': self.client_name,
            'document_type': self.document_type,
            'id_type': self.id_type,
            'id_number': self.id_number,
            'signature': self.signature,
            'notes': self.notes,
        }