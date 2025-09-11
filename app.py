from flask import Flask
from flask_cors import CORS
from routes.jobs import jobs_bp
from routes.service import service_bp
from routes.login import login_bp
from routes.contact import contact_bp
from routes.journal import journal_bp
from routes.messages import messages_bp
from routes.profile import profile_bp
from routes.contacts import clients_bp
from routes.calendar import calendar_bp
from routes.auth import auth_bp
from routes.mileage import mileage_bp
from routes.finances import finances_bp
from database.db import db

app = Flask(__name__)
allowed_origins = [
    "http://192.168.0.218:3000",
    "http://localhost:3001",
    "capacitor://localhost",   
    "http://localhost",         
    "http://localhost:3000"      
]
CORS(app, supports_credentials=True, resources={r"/*": {"origins": allowed_origins}}, allow_headers=["Content-Type", "Authorization", "x-user-id"])
app.config['SECRET_KEY'] = 'DaylynDavis2!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:DaylynDavis2!@localhost:3306/notary'  # Update as needed
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def index():
    return "Schirmer's Notary API is running."

app.register_blueprint(jobs_bp, url_prefix='/jobs')
app.register_blueprint(journal_bp, url_prefix='/journal')
app.register_blueprint(messages_bp, url_prefix='/messages')
app.register_blueprint(profile_bp, url_prefix='/profile')
app.register_blueprint(clients_bp, url_prefix='/clients')
app.register_blueprint(calendar_bp, url_prefix='/calendar')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(service_bp, url_prefix='/service')
app.register_blueprint(login_bp, url_prefix='/login')
app.register_blueprint(contact_bp, url_prefix='/contact')
app.register_blueprint(mileage_bp, url_prefix="/mileage")
app.register_blueprint(finances_bp, url_prefix="/finances")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
