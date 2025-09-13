from sqlalchemy import and_
from flask import Blueprint, jsonify, request, session, redirect, url_for, render_template
from models.job import JobRequest, AcceptedJob, DeniedJob
from models.user import User
from models.message import ClientContact, Message
from datetime import datetime
from .calendar import add_event_to_calendar
from database.db import db

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/admin/accepted/<int:job_id>', methods=['DELETE'])
def delete_accepted_job(job_id):
    job = AcceptedJob.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    return jsonify({"message": "Accepted job deleted successfully."}), 200

@jobs_bp.route('/admin/denied/<int:job_id>', methods=['DELETE'])
def delete_denied_job(job_id):
    job = DeniedJob.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    return jsonify({"message": "Denied job deleted successfully."}), 200

@jobs_bp.route('/admin/request/<int:request_id>', methods=['DELETE'])
def delete_service_request(request_id):
    job = JobRequest.query.get_or_404(request_id)
    db.session.delete(job)
    db.session.commit()
    return jsonify({"message": "Service request deleted successfully."}), 200

@jobs_bp.route('/admin/accepted/update-status', methods=['PATCH', 'OPTIONS'])
def update_accepted_job_status():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    data = request.get_json() or {}
    job_id = data.get('job_id')
    new_progress = data.get('progress')  # Should be 'upcoming', 'in_progress', or 'complete'
    if not job_id or not new_progress:
        return jsonify({"error": "Missing job_id or progress"}), 400
    job = AcceptedJob.query.get(job_id)
    if not job:
        return jsonify({"error": "Accepted job not found"}), 404
    job.progress = new_progress
    db.session.commit()
    return jsonify({"message": f"Progress updated to {new_progress}"}), 200

@jobs_bp.route('/admin/request/<int:request_id>', methods=['GET', 'OPTIONS'])
def get_single_job_request(request_id):
    job = JobRequest.query.get_or_404(request_id)
    return jsonify({
        "id": job.id,
        "name": job.name,
        "document_type": job.document_type,
        "service": job.service,
        "urgency": job.urgency,
        "service_date": job.service_date.strftime("%Y-%m-%d") if job.service_date else None,
        "description": job.description,
        "signers": job.signers,
        "id_verification": job.id_verification,
        "witnesses": job.witnesses,
        "location": job.location,
        "wording": job.wording,
        "status": job.status,
        "requested_by": job.requested_by,
        "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None,
        "email": job.email
    })


# Automatically update status to 'in_progress' if within an hour of service_date
def update_job_statuses():
    now = datetime.now()
    upcoming_jobs = AcceptedJob.query.filter_by(progress='upcoming').all()
    for job in upcoming_jobs:
        if job.service_date and (job.service_date - now).total_seconds() <= 3600:
            job.progress = 'in_progress'
    db.session.commit()




@jobs_bp.route('/request', methods=['POST', 'OPTIONS'])

def request_job():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    data = request.get_json()

    requested_by = session.get('user_id')
    if requested_by:
        user = User.query.get(requested_by)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        name = user.name
        client_email = user.email
    else:
        # Use submitted name/email for unauthenticated clients
        name = data.get('name')
        client_email = data.get('email')

    if not data:
        return jsonify({'error': 'Missing JSON payload'}), 400

    document_type = data.get('document_type')
    service = data.get('service')
    signers = data.get('signer', '')
    urgency = data.get('urgency', 'normal')
    date = data.get('date')
    location = data.get('location')

    doc_description = data.get('wording', '')
    id_verification = data.get('id_verification', 'no').lower() == 'yes'
    witnesses = 1 if data.get('witness') == 'yes' else 0

    if not all([name, document_type, service, signers, location]):
        return jsonify({'error': 'Missing required fields'}), 400

    client_contact = ClientContact.query.filter_by(email=client_email).first()
    if not client_contact:
        client_contact = ClientContact(name=name, email=client_email)
        db.session.add(client_contact)
        db.session.commit()
    client_email = client_contact.email

    job = JobRequest(
        name=name,
        document_type=document_type,
        service=service,
        urgency=urgency,
        service_date=datetime.strptime(date, "%Y-%m-%d") if date else None,
        description=doc_description,
        signers=signers,
        id_verification=id_verification,
        witnesses=witnesses,
        location=location,
        wording=doc_description,
        status="pending",
        requested_by=requested_by if requested_by else None,
        email=client_email
    )

    db.session.add(job)
    db.session.commit()

    existing_contact = ClientContact.query.filter_by(email=client_email).first()
    if not existing_contact:
        contact = ClientContact(
            name=name,
            email=client_email,
            first_request_id=job.id
        )
        db.session.add(contact)
        db.session.commit()

    if client_contact:
        welcome_message = Message(
            from_admin=True,
            content="Thank you for choosing my services. I will get back to you as swiftly as possible.",
            client_id=client_contact.id
        )
        db.session.add(welcome_message)
        db.session.commit()

    return jsonify({
        "message": "Job request submitted successfully",
        "job_id": job.id
    }), 201
    
@jobs_bp.route('/admin/request/<int:request_id>')
def view_request(request_id):
    job_request = JobRequest.query.get_or_404(request_id)

    return jsonify({
        "id": job_request.id,
        "name": job_request.name,
        "email": job_request.email,
        "document_type": job_request.document_type,
        "service": job_request.service,
        "urgency": job_request.urgency,
        "service_date": job_request.service_date.strftime("%Y-%m-%d") if job_request.service_date else None,
        "description": job_request.description,
        "signers": job_request.signers,
        "id_verification": job_request.id_verification,
        "witnesses": job_request.witnesses,
        "location": job_request.location,
        "wording": job_request.wording,
        "status": job_request.status,
        "requested_by": job_request.requested_by,
        "created_at": job_request.created_at.strftime("%Y-%m-%d %H:%M:%S") if job_request.created_at else None
    })

@jobs_bp.route('/admin/request/<int:request_id>/accept', methods=['POST'])
def accept_request(request_id):
    job = JobRequest.query.get_or_404(request_id)
    data = request.get_json() or {}
    new_service_date = data.get('service_date')
    if new_service_date:
        try:
            job.service_date = datetime.strptime(new_service_date[:10], "%Y-%m-%d")
        except Exception:
            return jsonify({"error": "Invalid date format"}), 400
        db.session.commit()

    progress = 'upcoming'
    if job.service_date:
        now = datetime.now()
        if (job.service_date - now).total_seconds() <= 3600:
            progress = 'in_progress'

    accepted = AcceptedJob(
        name=job.name,
        document_type=job.document_type,
        signers=job.signers,
        id_verification=job.id_verification,
        witnesses=job.witnesses,
        location=job.location,
        service_date=job.service_date,
        wording=job.wording,
        requested_by=job.requested_by,
        payment_method=None,
        email=job.email,
        notes=data.get('notes'),
        progress=progress
    )
    db.session.add(accepted)

    # Create a calendar event for this accepted job
    event_data = {
        'title': f'Service: {job.service} for {job.name}',
        'start_date': job.service_date or job.created_at,
        'end_date': job.service_date or job.created_at,
        'description': job.description or '',
        'location': job.location,
        'user_id': job.requested_by if job.requested_by else 1  # Use default user_id if None
    }
    add_event_to_calendar(event_data)  # Your calendar helper

    # Remove from pending
    db.session.delete(job)
    db.session.commit()

    # Send message to client
    client_contact = ClientContact.query.filter_by(email=accepted.email).first()
    if client_contact:
        msg = Message(
            from_admin=True,
            content="I am happy to work with you! Be on the lookout for future communication with any extra information.",
            client_id=client_contact.id
        )
        db.session.add(msg)
        db.session.commit()

    return jsonify({"message": "Job accepted successfully"}), 200

@jobs_bp.route('/admin/request/<int:request_id>/deny', methods=['POST'])
def deny_job(request_id):
    job = JobRequest.query.get_or_404(request_id)

    denied = DeniedJob(
        name=job.name,
        document_type=job.document_type,
        signers=job.signers,
        id_verification=job.id_verification,
        witnesses=job.witnesses,
        location=job.location,
        wording=job.description,
        requested_by=job.requested_by,
        reason="Undisclosed",
        email=job.email
    )
    db.session.add(denied)

    db.session.delete(job)
    db.session.commit()

    client_contact = ClientContact.query.filter_by(email=denied.email).first()
    if client_contact:
        msg = Message(
            from_admin=True,
            content="I am unable to make this request happen for undisclosed reasons. If you have further questions about my decision please contact me.",
            client_id=client_contact.id
        )
        db.session.add(msg)
        db.session.commit()

    return jsonify({"message": "Job denied successfully"}), 200

@jobs_bp.route('/', methods=['GET'])
def get_job_requests():
    # Get all jobs for all statuses
    pending_jobs = JobRequest.query.filter_by(status='pending').all()
    accepted_jobs = AcceptedJob.query.all()
    denied_jobs = DeniedJob.query.all()
    jobs = []
    for job in pending_jobs:
        jobs.append({
            "id": job.id,
            "name": job.name,
            "document_type": job.document_type,
            "service": job.service,
            "urgency": job.urgency,
            "service_date": job.service_date.strftime("%Y-%m-%d") if job.service_date else None,
            "description": job.description,
            "signers": job.signers,
            "id_verification": job.id_verification,
            "witnesses": job.witnesses,
            "location": job.location,
            "wording": job.wording,
            "status": "pending",
            "requested_by": job.requested_by,
            "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None
        })
    for job in accepted_jobs:
        jobs.append({
            "id": job.id,
            "name": job.name,
            "document_type": job.document_type,
            "service": None,
            "urgency": None,
            "service_date": job.service_date.strftime("%Y-%m-%d") if job.service_date else None,
            "description": None,
            "signers": job.signers,
            "id_verification": job.id_verification,
            "witnesses": job.witnesses,
            "location": job.location,
            "wording": job.wording,
            "status": "accepted",
            "progress": job.progress,  # 'upcoming', 'in_progress', 'complete'
            "requested_by": job.requested_by,
            "created_at": job.accepted_at.strftime("%Y-%m-%d %H:%M:%S") if job.accepted_at else None
        })
    for job in denied_jobs:
        jobs.append({
            "id": job.id,
            "name": job.name,
            "document_type": job.document_type,
            "service": None,
            "urgency": None,
            "service_date": None,
            "description": None,
            "signers": job.signers,
            "id_verification": job.id_verification,
            "witnesses": job.witnesses,
            "location": job.location,
            "wording": job.wording,
            "status": "denied",
            "requested_by": job.requested_by,
            "created_at": job.denied_at.strftime("%Y-%m-%d %H:%M:%S") if job.denied_at else None
        })
    return jsonify(jobs)

@jobs_bp.route('/client/request/status', methods=['GET'])
def client_request_status():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    # Check pending jobs
    job = JobRequest.query.filter_by(requested_by=user_id).order_by(JobRequest.created_at.desc()).first()
    if job:
        return jsonify({
            "status": job.status,
            "payment_status": None,
            "request_id": job.id,
            "name": job.name,
            "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    # Check accepted jobs
    accepted = AcceptedJob.query.filter_by(requested_by=user_id).order_by(AcceptedJob.accepted_at.desc()).first()
    if accepted:
        return jsonify({
            "status": "accepted",
            "payment_status": accepted.payment_method or "Pending",
            "request_id": accepted.id,
            "name": accepted.name,
            "created_at": accepted.accepted_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    # Check denied jobs
    denied = DeniedJob.query.filter_by(requested_by=user_id).order_by(DeniedJob.denied_at.desc()).first()
    if denied:
        return jsonify({
            "status": "denied",
            "reason": denied.reason or "Not specified",
            "request_id": denied.id,
            "name": denied.name,
            "created_at": denied.denied_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify({
        "status": "No request found"
    })

@jobs_bp.route('/client/requests', methods=['GET'])
def get_all_client_requests():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    # Combine all 3 job categories
    job_requests = JobRequest.query.filter_by(requested_by=user_id).order_by(JobRequest.created_at.desc()).all()
    accepted_jobs = AcceptedJob.query.filter_by(requested_by=user_id).order_by(AcceptedJob.accepted_at.desc()).all()
    denied_jobs = DeniedJob.query.filter_by(requested_by=user_id).order_by(DeniedJob.denied_at.desc()).all()

    def format_job(job, status):
        return {
            "id": job.id,
            "name": job.name,
            "status": status,
            "document_type": job.document_type,
            "created_at": getattr(job, 'created_at', getattr(job, 'accepted_at', getattr(job, 'denied_at', None))).strftime("%Y-%m-%d %H:%M:%S"),
        }

    combined = [format_job(j, "pending") for j in job_requests] + \
               [format_job(a, "accepted") for a in accepted_jobs] + \
               [format_job(d, "denied") for d in denied_jobs]

    return jsonify({"requests": combined})

@jobs_bp.route('/company/requests/<company_id>', methods=['GET'])
def get_company_requests(company_id):
    # Example: filter jobs by company_id (assuming you have a company_id field)
    jobs = JobRequest.query.filter_by(company_id=company_id).all()
    return jsonify({
        "requests": [
            {
                "id": j.id,
                "name": j.name,
                "status": j.status,
                "company_id": j.company_id
            } for j in jobs
        ]
    })

@jobs_bp.route('/admin/accepted/<int:job_id>', methods=['GET'])
def view_accepted_job(job_id):
    update_job_statuses()
    job = AcceptedJob.query.get_or_404(job_id)
    return jsonify({
        "id": job.id,
        "name": job.name,
        "document_type": job.document_type,
        "service_date": job.service_date.strftime("%Y-%m-%d") if job.service_date else None,
        "signers": job.signers,
        "id_verification": job.id_verification,
        "witnesses": job.witnesses,
        "location": job.location,
        "wording": job.wording,
        "payment_method": job.payment_method,
        "requested_by": job.requested_by,
        "accepted_at": job.accepted_at.strftime("%Y-%m-%d %H:%M:%S") if job.accepted_at else None,
        "email": job.email,
        "progress": job.progress
    })

@jobs_bp.route('/admin/denied/<int:job_id>', methods=['GET'])
def view_denied_job(job_id):
    job = DeniedJob.query.get_or_404(job_id)
    return jsonify({
        "id": job.id,
        "name": job.name,
        "document_type": job.document_type,
        "signers": job.signers,
        "id_verification": job.id_verification,
        "witnesses": job.witnesses,
        "location": job.location,
        "wording": job.wording,
        "requested_by": job.requested_by,
        "denied_at": job.denied_at.strftime("%Y-%m-%d %H:%M:%S") if job.denied_at else None,
        "reason": job.reason,
        "email": job.email
    })

# Automatically update status to 'in_progress' if within an hour of service_date
def update_job_statuses():
    now = datetime.now()
    upcoming_jobs = AcceptedJob.query.filter_by(progress='upcoming').all()
    for job in upcoming_jobs:
        if job.service_date and (job.service_date - now).total_seconds() <= 3600:
            job.progress = 'in_progress'
    db.session.commit()

@jobs_bp.route('/admin/accepted/<int:job_id>/complete', methods=['POST'])
def mark_job_complete(job_id):
    job = AcceptedJob.query.get_or_404(job_id)
    job.progress = 'complete'
    db.session.commit()
    return jsonify({"message": "Job marked as complete."}), 200

@jobs_bp.route('/admin/accepted/<int:job_id>/edit', methods=['PATCH'])
def edit_accepted_job(job_id):
    job = AcceptedJob.query.get_or_404(job_id)
    data = request.get_json() or {}
    updated = False

    # Update all editable fields
    if 'name' in data:
        job.name = data['name']
        updated = True
    if 'document_type' in data:
        job.document_type = data['document_type']
        updated = True
    if 'signers' in data:
        job.signers = data['signers']
        updated = True
    if 'witnesses' in data:
        job.witnesses = data['witnesses']
        updated = True
    if 'location' in data:
        job.location = data['location']
        updated = True
    if 'service_date' in data:
        try:
            # Accept both date and datetime-local formats
            if 'T' in data['service_date']:
                job.service_date = datetime.strptime(data['service_date'], "%Y-%m-%dT%H:%M")
            else:
                job.service_date = datetime.strptime(data['service_date'][:10], "%Y-%m-%d")
            updated = True
        except Exception:
            return jsonify({"error": "Invalid date format"}), 400
    if 'wording' in data:
        job.wording = data['wording']
        updated = True
    if 'notes' in data:
        job.notes = data['notes']
        updated = True
    if 'progress' in data:
        job.progress = data['progress']
        updated = True

    db.session.commit()

    if updated:
        # Update calendar event with new job details
        event_data = {
            'title': f'Service: {job.document_type} for {job.name}',
            'start_date': job.service_date,
            'end_date': job.service_date,
            'description': job.wording or '',
            'location': job.location,
            'user_id': job.requested_by if job.requested_by else 1
        }
        add_event_to_calendar(event_data)
        return jsonify({"message": "Appointment updated successfully."}), 200
    else:
        return jsonify({"message": "No changes made."}), 200
    
