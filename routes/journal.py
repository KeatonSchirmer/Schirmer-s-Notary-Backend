from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from reportlab.pdfgen import canvas
from models.journal import JournalEntry, PDF, JournalSigner
from database.db import db
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os
from werkzeug.utils import secure_filename
from datetime import datetime

journal_bp = Blueprint('journal', __name__, template_folder='frontend/templates')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'database', 'journal_docs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@journal_bp.route('/', methods=['GET'])
def get_journal_entries():
    entries = JournalEntry.query.all()
    result = []
    for entry in entries:
        result.append({
            'id': entry.id,
            'date': entry.date.strftime("%Y-%m-%d"),
            'location': entry.location,
            'document_type': entry.document_type,
            'id_verification': entry.id_verification,
            'notes': entry.notes,
            'signers': [
                {
                    'name': signer.name,
                    'address': signer.address,
                    'phone': signer.phone
                }
                for signer in entry.signers
            ]
        })
    return jsonify(result)

@journal_bp.route('/new', methods=['POST'])
def new_entry():
    if request.is_json:
        data = request.get_json()
        signers_data = data.get('signers', [])
        entry = JournalEntry(
            date=datetime.strptime(data.get('date'), "%Y-%m-%d"),
            location=data.get('location'),
            document_type=data.get('document_type'),
            id_verification=data.get('id_verification', False),
            notes=data.get('notes')
        )
        db.session.add(entry)
        db.session.flush()

        for signer in signers_data:
            signer_obj = JournalSigner(
                journal_id=entry.id,
                name=signer.get('name'),
                address=signer.get('address'),
                phone=signer.get('phone')
            )
            db.session.add(signer_obj)

        db.session.commit()
        return jsonify({'message': 'Journal entry created successfully', 'id': entry.id}), 201
    else:
        return jsonify({'error': 'Request must be JSON'}), 400

@journal_bp.route('/<int:entry_id>', methods=['GET'])
def get_entry(entry_id):
    entry = JournalEntry.query.get(entry_id)
    if entry:
        return jsonify(entry={
            'id': entry.id,
            'date': entry.date.strftime('%Y-%m-%d') if entry.date else None,
            'location': entry.location,
            'document_type': entry.document_type,
            'id_verification': entry.id_verification,
            'notes': entry.notes,
            'signers': [
                {
                    'name': signer.name,
                    'address': signer.address,
                    'phone': signer.phone
                }
                for signer in entry.signers
            ]
        })
    else:
        return jsonify(error="Not found"), 404

@journal_bp.route('/<int:entry_id>/pdf', methods=['GET'])
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
    p.drawString(x_margin, y, f"Date: {entry.date.strftime('%Y-%m-%d') if entry.date else 'N/A'}")
    y -= 20
    p.drawString(x_margin, y, f"Location: {entry.location or 'N/A'}")
    y -= 20
    p.drawString(x_margin, y, f"Document Type: {entry.document_type}")
    y -= 20
    p.drawString(x_margin, y, f"ID Verified: {'Yes' if entry.id_verification else 'No'}")
    y -= 20

    # List all signers
    if entry.signers:
        for idx, signer in enumerate(entry.signers, start=1):
            p.drawString(x_margin, y, f"Signer {idx}: {signer.name}")
            y -= 20
            p.drawString(x_margin + 20, y, f"Address: {signer.address or 'N/A'}")
            y -= 20
            p.drawString(x_margin + 20, y, f"Phone: {signer.phone or 'N/A'}")
            y -= 20
    else:
        p.drawString(x_margin, y, "No signers listed.")
        y -= 20

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

@journal_bp.route('/<int:entry_id>/upload', methods=['POST'])
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

    pdf_record = PDF(filename=filename, file_path=save_path, journal=entry.id)
    db.session.add(pdf_record)
    db.session.commit()

    return jsonify({"message": "Document uploaded", "pdf_id": pdf_record.id, "file_path": save_path})

@journal_bp.route('/<int:entry_id>/pdfs', methods=['GET'])
def get_entry_pdfs(entry_id):
    entry = JournalEntry.query.get(entry_id)
    if not entry:
        return jsonify({"error": "Journal entry not found"}), 404
    pdfs = PDF.query.filter_by(journal=entry.id).all()
    return jsonify({
        "pdfs": [
            {"id": pdf.id, "filename": pdf.filename, "file_path": pdf.file_path}
            for pdf in pdfs
        ]
    })

@journal_bp.route('/pdf/<int:pdf_id>', methods=['GET'])
def get_pdf(pdf_id):
    pdf = PDF.query.get(pdf_id)
    if not pdf or not os.path.exists(pdf.file_path):
        return jsonify({"error": "PDF not found"}), 404
    return send_file(pdf.file_path, as_attachment=True)