from database.db import db
import datetime

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    from_admin = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    client_id = db.Column(db.Integer, db.ForeignKey('client_contact.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "from": self.sender,
            "content": self.content,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M")
        }

class ClientContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    first_request_id = db.Column(db.Integer, db.ForeignKey('job_request.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())  