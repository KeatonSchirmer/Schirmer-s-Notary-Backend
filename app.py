from flask import Flask, request, session, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
import requests
import os
from routes.jobs import jobs_bp
from routes.journal import journal_bp
from routes.clients import clients_bp
from routes.calendar import calendar_bp
from routes.auth import auth_bp
from routes.mileage import mileage_bp
from routes.finances import finances_bp
from routes.square import square_bp
from database.db import db
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

def send_push_notification(token, title, body):
    message = {
        'to': token,
        'sound': 'default',
        'title': title,
        'body': body,
    }
    response = requests.post(
        'https://exp.host/--/api/v2/push/send',
        json=message,
        headers={'Content-Type': 'application/json'}
    )
    return response.json()

app = Flask(__name__)

# Configure CORS with environment-specific origins
allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app, 
     supports_credentials=True, 
     resources={r"/*": {"origins": allowed_origins}}, 
     allow_headers=["Content-Type", "Authorization", "x-user-id", "X-User-Id"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

if not app.config['SECRET_KEY']:
    raise ValueError("SECRET_KEY environment variable is required")
if not app.config['SQLALCHEMY_DATABASE_URI']:
    raise ValueError("DATABASE_URL environment variable is required")

db.init_app(app)
@app.before_request
def log_origin():
    origin = request.headers.get('Origin')
    logging.info(f"Request Origin: {origin}")

@app.route('/')
def index():
    return "Schirmer's Notary API is running."

@app.route('/session', methods=['GET'])
def get_session():
    user_id = session.get("user_id")
    user_type = session.get("user_type")
    username = session.get("username")
    
    # If we have a user_id, fetch their current data
    if user_id and user_type:
        try:
            from models.accounts import Admin, Client
            if user_type == 'admin':
                user = Admin.query.get(user_id)
                if user:
                    username = user.name
            elif user_type == 'client':
                user = Client.query.get(user_id)
                if user:
                    username = user.name
        except Exception as e:
            print(f"Error fetching user data in session: {e}")
    
    return jsonify({
        "user_id": user_id,
        "user_type": user_type,
        "username": username,
        "logged_in": bool(user_id)
    })

@app.route('/api/save-push-token', methods=['POST'])
def save_push_token():
    data = request.get_json()
    token = data.get('token')
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    if not user_id or not token:
        return {'success': False, 'error': 'Missing user or token'}, 400

    from models.accounts import Admin
    from models.accounts import Client
    user = None
    if user_type == 'admin':
        user = Admin.query.get(user_id)
    elif user_type == 'client':
        user = Client.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}, 404

    user.push_token = token
    db.session.commit()
    return {'success': True}

migrate = Migrate(app, db)

app.register_blueprint(jobs_bp, url_prefix='/jobs')
app.register_blueprint(journal_bp, url_prefix='/journal')
app.register_blueprint(clients_bp, url_prefix='/clients')
app.register_blueprint(calendar_bp, url_prefix='/calendar')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(mileage_bp, url_prefix="/mileage")
app.register_blueprint(finances_bp, url_prefix="/finances")
app.register_blueprint(square_bp, url_prefix="/square")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
