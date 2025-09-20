from flask import Flask, request, session, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from routes.jobs import jobs_bp
from routes.journal import journal_bp
from routes.clients import clients_bp
from routes.calendar import calendar_bp
from routes.auth import auth_bp
from routes.mileage import mileage_bp
from routes.finances import finances_bp
from database.db import db
from werkzeug.security import generate_password_hash
import logging
from utils.scheduler import start_scheduler


app = Flask(__name__)

allowed_origins = [
    'https://schirmer-s-notary-admin-site.onrender.com',
    'https://schirmer-s-notary-main-site.onrender.com',
    "*",
    "http://schirmersnotary.com",
    "http://www.schirmersnotary.com",
    "capacitor://localhost",
    "ionic://localhost",
    "http://localhost",
    "null",
]
CORS(app, supports_credentials=True, resources={r"/*": {"origins": allowed_origins}}, allow_headers=["Content-Type", "Authorization", "x-user-id"])
app.config['SECRET_KEY'] = 'DaylynDavis2!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:DaylynDavis2!@localhost:3306/notary'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://schirmersnotary_user:lRpAqU1MOPm0BvC6TQGH9jQo1sCxKWeH@dpg-d323vmjipnbc73csma5g-a:5432/schirmersnotary'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    return jsonify({
        "user_id": session.get("user_id"),
        "user_type": session.get("user_type"),
        "username": session.get("username")
    })

migrate = Migrate(app, db)

app.register_blueprint(jobs_bp, url_prefix='/jobs')
app.register_blueprint(journal_bp, url_prefix='/journal')
app.register_blueprint(clients_bp, url_prefix='/clients')
app.register_blueprint(calendar_bp, url_prefix='/calendar')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(mileage_bp, url_prefix="/mileage")
app.register_blueprint(finances_bp, url_prefix="/finances")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)