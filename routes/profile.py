from flask import jsonify, session, Blueprint, request
from models.user import User
from database.db import db
import traceback
from datetime import datetime

profile_bp = Blueprint('profile', __name__, template_folder='frontend/templates')

@profile_bp.route('/', methods=['GET'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        "name": user.name,
        "email": user.email,
        "license_expiration": getattr(user, "license_expiration", None),
        "base_location": getattr(user, "base_location", None),
        "home_address": getattr(user, "home_address", None),
    })

@profile_bp.route('/update', methods=['PATCH'])
def update_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Not logged in"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    

    data = request.get_json()

    if 'license_expiration' in data:
        try:
            user.license_expiration = datetime.strptime(data['license_expiration'], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    

    try:

        # Fields shared by both roles
        user.name = data.get('name', user.name)
        user.email = data.get('email', user.email)
        user.phone = data.get('phone', user.phone)
    

        if user.is_admin == 'true':
            user.office_address = data.get('office_address', user.office_address)
            user.notary_license_number = data.get('notary_license_number', user.notary_license_number)
            user.license_expiration = data.get('license_expiration', user.license_expiration)
            user.state_of_commission = data.get('state_of_commission', user.state_of_commission)
            user.bonding_company = data.get('bonding_company', user.bonding_company)
            user.eo_insurance_info = data.get('eo_insurance_info', user.eo_insurance_info)
            user.background_check = data.get('background_check', user.background_check)
            user.travel_radius = data.get('travel_radius', user.travel_radius)
            user.availability = data.get('availability', user.availability)
            user.service_types = data.get('service_types', user.service_types)
            user.language = data.get('language', user.language)
            user.bank_info = data.get('bank_info', user.bank_info)

        elif user.is_admin == 'false':
            user.home_address = data.get('home_address', user.home_address) 
            user.business_name = data.get('business_name', user.business_name)
            user.billing_address = data.get('billing_address', user.billing_address)
            user.special_needs = data.get('special_needs', user.special_needs)
            user.payment_method = data.get('payment_method', user.payment_method) 

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    for field in [
                'name', 'email', 'phone', 'office_address', 'notary_license_number',
                'license_expiration', 'state_of_commission', 'bonding_company',
                'eo_insurance_info', 'background_check', 'travel_radius',
                'availability', 'service_types', 'language', 'bank_info'
            ]:
                if field in data and data[field].strip() != '':
                    setattr(user, field, data[field])

    db.session.commit()

    return jsonify({
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "office_address": user.office_address,
        "role": user.is_admin,
        "notary_license_number": getattr(user, "notary_license_number", None),
        "license_expiration": getattr(user, "license_expiration", None),
        "state_of_commission": getattr(user, "state_of_commission", None),
        "bonding_company": getattr(user, "bonding_company", None),
        "eo_insurance_info": getattr(user, "eo_insurance_info", None),
        "background_check": getattr(user, "background_check", None),
        "travel_radius": getattr(user, "travel_radius", None),
        "availability": getattr(user, "availability", None),
        "service_types": getattr(user, "service_types", None),
        "language": getattr(user, "language", None),
        "bank_info": getattr(user, "bank_info", None),
        "home_address": getattr(user, "home_address", None),
        "business_name": getattr(user, "business_name", None),
        "billing_address": getattr(user, "billing_address", None),
        "special_needs": getattr(user, "special_needs", None),
        "payment_method": getattr(user, "payment_method", None)
    })