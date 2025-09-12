from database.db import db

class User(db.Model):

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(10))
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    office_address = db.Column(db.String(255), nullable=True)
    notary_license_number = db.Column(db.String(100), nullable=True)
    license_expiration = db.Column(db.String(20), nullable=True)
    state_of_commission = db.Column(db.String(100), nullable=True)
    bonding_company = db.Column(db.String(100), nullable=True)
    eo_insurance_info = db.Column(db.String(255), nullable=True)
    background_check = db.Column(db.String(255), nullable=True)
    travel_radius = db.Column(db.String(50), nullable=True)
    availability = db.Column(db.Text, nullable=True)
    service_types = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(100), nullable=True)
    notifications_enabled = db.Column(db.Boolean, default=True)
    bank_info = db.Column(db.String(255), nullable=True)
    profile_pic_url = db.Column(db.String(255))
    password_hash = db.Column(db.String(255))
    two_factor_enabled = db.Column(db.Boolean, default=False)
    home_address = db.Column(db.String(255), nullable=True)
    business_name = db.Column(db.String(255), nullable=True)
    billing_address = db.Column(db.String(255), nullable=True)
    special_needs = db.Column(db.String(225), nullable=True)
    payment_method = db.Column(db.String(220), nullable=True)
    
