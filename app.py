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
from models.user import User
from werkzeug.security import generate_password_hash

app = Flask(__name__)
allowed_origins = [
    "http://192.168.0.218:3000",
    "http://localhost:3001",
    "capacitor://localhost",   
    "http://localhost",         
    "http://localhost:3000",
    'https://schirmer-s-notary-admin-site.onrender.com',
    'https://schirmer-s-notary-main-site.onrender.com'
]
CORS(app, supports_credentials=True, resources={r"/*": {"origins": allowed_origins}}, allow_headers=["Content-Type", "Authorization", "x-user-id"])
app.config['SECRET_KEY'] = 'DaylynDavis2!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:DaylynDavis2!@localhost:3306/notary'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://schirmersnotary_user:lRpAqU1MOPm0BvC6TQGH9jQo1sCxKWeH@dpg-d323vmjipnbc73csma5g-a:5432/schirmersnotary'  # Update with your Render PostgreSQL credentials
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

def create_admin():
    with app.app_context():
        admin = User.query.filter_by(email="keasch1589@gmail.com").first()
        if not admin:
            admin = User(
                email="keasch1589@gmail.com",
                is_admin=True,
                name="Admin Name",
                password_hash=generate_password_hash("Thunder1589@"),
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(host='0.0.0.0', port=5000, debug=True)
