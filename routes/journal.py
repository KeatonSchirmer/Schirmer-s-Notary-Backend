from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from io import BytesIO
from reportlab.pdfgen import canvas
from models.journal import JournalEntry
from database.db import db
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os
from werkzeug.utils import secure_filename



journal_bp = Blueprint('journal', __name__, template_folder='frontend/templates')


UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'database', 'journal_docs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



@journal_bp.route('/', methods=['GET'])
def get_journal_entries():
    entries = JournalEntry.query.order_by(JournalEntry.date.desc()).all()
    data = [{
        'id': entry.id,
        'date': entry.date,
        'client_name': entry.client_name,
        'document_type': entry.document_type,
        'id_type': entry.id_type,
        'id_number': entry.id_number,
        'signature': entry.signature,
        'notes': entry.notes
    } for entry in entries]
    return jsonify({'entries': data})

@journal_bp.route('/journal/new', methods=['POST'])
def new_entry():
    if request.is_json:
        data = request.get_json()
        entry = JournalEntry(
            date=data.get('date'),
            client_name=data.get('client_name'),
            document_type=data.get('document_type'),
            id_type=data.get('id_type'),
            id_number=data.get('id_number'),
            signature=data.get('signature'),
            notes=data.get('notes')
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'Journal entry created successfully'}), 201
    else:
        return jsonify({'error': 'Request must be JSON'}), 400
    
@journal_bp.route('/journal/<int:entry_id>', methods=['GET'])
def get_entry(entry_id):
    entry = JournalEntry.query.get(entry_id)
    if entry:
        return jsonify(entry=entry.to_dict())
    else:
        return jsonify(error="Not found"), 404

@journal_bp.route('/journal/<int:entry_id>/pdf')
def generate_pdf(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    x_margin = inch
    y = height - inch

    p.setFont("Helvetica-Bold", 14)
    p.drawString(x_margin, y, f"Journal Entry #{entry.id}")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(x_margin, y, f"Client: {entry.client_name}")
    y -= 20
    p.drawString(x_margin, y, f"Date: {entry.date.strftime('%Y-%m-%d') if entry.date else 'N/A'}")
    y -= 20
    p.drawString(x_margin, y, f"Document Type: {entry.document_type}")
    y -= 20
    p.drawString(x_margin, y, f"ID Type: {entry.id_type}")
    y -= 20
    p.drawString(x_margin, y, f"ID Number: {entry.id_number}")
    y -= 20
    p.drawString(x_margin, y, f"Signature: {entry.signature}")
    y -= 20

    # Handle multiline notes
    notes = entry.notes or ''
    textobject = p.beginText(x_margin, y)
    textobject.textLines(f"Notes:\n{notes}")
    p.drawText(textobject)

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'Journal_{entry.id}.pdf',
        mimetype='application/pdf'
    )

@journal_bp.route('/journal/<int:entry_id>/upload', methods=['POST'])
def upload_document(entry_id):
    entry = JournalEntry.query.get(entry_id)
    if not entry:
        return jsonify({"error": "Journal entry not found"}), 404

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    entry.document_path = save_path
    db.session.commit()

    return jsonify({"message": "Document uploaded", "document_path": save_path})

@journal_bp.route('/journal/<int:entry_id>/document', methods=['GET'])
def get_document(entry_id):
    entry = JournalEntry.query.get(entry_id)
    if not entry or not entry.document_path:
        return jsonify({"error": "Document not found"}), 404
    return send_file(entry.document_path, as_attachment=True)

