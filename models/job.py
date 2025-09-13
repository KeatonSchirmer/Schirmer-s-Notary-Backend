from database.db import db
from datetime import datetime

class JobRequest(db.Model):
    __tablename__ = 'job_request'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)                # Who's requesting
    document_type = db.Column(db.String(50), nullable=False)        # Acknowledgment, Jurat, etc.
    service = db.Column(db.String(50), nullable=False, default='Mobile')  # Service type
    urgency = db.Column(db.String(20), nullable=False, default='normal')  # Urgency level
    service_date = db.Column(db.DateTime, nullable=True)                   # When it's needed
    description = db.Column(db.Text, nullable=True)                # Description of the job
    signers = db.Column(db.String(255), nullable=False)             # Signers info
    id_verification = db.Column(db.Boolean, default=False)          # Valid ID?
    witnesses = db.Column(db.Integer, nullable=False, default=1)    # Number of witnesses
    location = db.Column(db.String(255), nullable=False)            # Where it's happening
    wording = db.Column(db.Text, nullable=True)                     # Special wording?
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending / accepted / denied
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    client_contact = db.relationship('ClientContact', backref='first_request', uselist=False)
    email = db.Column(db.String(120))
    company_id = db.Column(db.String(100), nullable=True)  # Add this line for company filtering

    def __repr__(self):
        return f'<JobRequest {self.name} - {self.document_type}>'
    
class AcceptedJob(db.Model):
    __tablename__ = 'accepted_jobs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    service_date = db.Column(db.DateTime, nullable=True)
    signers = db.Column(db.String(255), nullable=False)
    id_verification = db.Column(db.Boolean, default=False)
    witnesses = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    wording = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    accepted_at = db.Column(db.DateTime, server_default=db.func.now())
    email = db.Column(db.String(120))
    notes = db.Column(db.Text, nullable=True)
    progress = db.Column(db.String(20), nullable=False, default='upcoming')

class DeniedJob(db.Model):
    __tablename__ = 'denied_jobs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    signers = db.Column(db.String(255), nullable=False)
    id_verification = db.Column(db.Boolean, default=False)
    witnesses = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    wording = db.Column(db.Text, nullable=True)
    denied_at = db.Column(db.DateTime, server_default=db.func.now())
    reason = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(120))


class PDF(db.Model):
    __tablename__ = "pdfs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    # Optionally store file content as binary:
    # data = db.Column(db.LargeBinary, nullable=True)
    # Or store the file path:
    file_path = db.Column(db.String(512), nullable=True)