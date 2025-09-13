from flask import Blueprint, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/contact', methods=['POST'])
def send_contact_email():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    if not all([name, email, message]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Email settings
    to_email = 'schirmer.nikolas@gmail.com'
    subject = f'New Contact Message from {name}'
    body = f"Name: {name}\nEmail: {email}\nMessage:\n{message}"

    # SMTP config (example for Gmail)
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = 'schirmer.nikolas@gmail.com'
    smtp_pass = 'cgyqzlbjwrftwqok'

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return jsonify({'message': 'Email sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
