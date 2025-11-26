import os
import threading
import time
import logging
import requests
from flask import Blueprint, request, jsonify
from square import Square

square_bp = Blueprint('square', __name__)
logger = logging.getLogger("square_poll")

client = Square(
    environment='production',
    token = os.environ.get("SQUARE_ACCESS_TOKEN", "")
)

#* Switching the following to be created on the frontend
# Update Customer
# Search subscriptions
# Upsert subscription
# Upsert service
# Calculate order
#

def square_base_url():
    env = os.environ.get("SQUARE_ENV", "sandbox").lower()
    return "https://connect.squareupsandbox.com" if env == "sandbox" else "https://connect.squareup.com"

def square_headers():
    token = os.environ.get("SQUARE_ACCESS_TOKEN", "")
    return {
        "Square-Version": os.environ.get("SQUARE_API_VERSION", "2025-09-24"),
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def fetch_all_square_customers():
    customers = []
    url = f"{square_base_url()}/v2/customers"
    params = {}
    try:
        while True:
            r = requests.get(url, headers=square_headers(), params=params, timeout=15)
            r.raise_for_status()
            body = r.json()
            page_customers = body.get("customers") or []
            customers.extend(page_customers)
            cursor = body.get("cursor")
            if not cursor:
                break
            params["cursor"] = cursor
    except requests.HTTPError as he:
        logger.exception("Square customers fetch failed: %s", he)
    except Exception:
        logger.exception("Unexpected error fetching Square customers")
    return customers

def find_local_user_for_customer(customer):
    try:
        from models import db
        from models.accounts import Client
    except Exception:
        try:
            from models import db
            from models import Client
        except Exception as e:
            logger.exception("Unable to import models: %s", e)
            return None, None, None

    email = (customer.get("email_address") or "").strip().lower()
    given = (customer.get("given_name") or "").strip()
    family = (customer.get("family_name") or "").strip()
    fullname = (given + " " + family).strip()
    square_id = customer.get("id")

    try:
        found = Client.query.filter_by(square_customer_id=square_id).first()
        if found:
            return found, db, Client
        if found:
            return found, db
    except Exception:
        logger.debug("Error querying by square_customer_id; continuing")

    if email:
        try:
            found = Client.query.filter(Client.email.ilike(email)).first()
            if found:
                return found, db, Client
        except Exception:
            pass
        try:
            if found:
                return found, db
        except Exception:
            pass

    if fullname:
        try:
            found = Client.query.filter(Client.name.ilike(f"%{fullname}%")).first()
            if found:
                return found, db, Client
        except Exception:
            pass
        try:
            if found:
                return found, db
        except Exception:
            pass

    return None, db, None

def link_customer_to_local_user(customer):
    square_id = customer.get("id")
    if not square_id:
        return False
    found_user, db, Model = find_local_user_for_customer(customer)
    if not found_user:
        logger.debug("No local match found for Square customer %s (%s)", square_id, customer.get("email_address"))
        return False
    try:
        # Only set if not already set
        if getattr(found_user, "square_customer_id", None) != square_id:
            setattr(found_user, "square_customer_id", square_id)
            db.session.add(found_user)
            db.session.commit()
            logger.info("Linked Square customer %s to local user id=%s", square_id, getattr(found_user, "id", None))
            return True
    except Exception:
        logger.exception("Failed to link Square customer %s to local user", square_id)
        try:
            db.session.rollback()
        except Exception:
            pass
    return False

def customer_polling_worker(interval_seconds=300):
    logger.info("Starting Square customer polling worker (interval=%s seconds)", interval_seconds)
    while True:
        try:
            customers = fetch_all_square_customers()
            logger.debug("Fetched %d Square customers", len(customers))
            for c in customers:
                try:
                    link_customer_to_local_user(c)
                except Exception:
                    logger.exception("Error processing customer: %s", c.get("id"))
        except Exception:
            logger.exception("Polling loop error")
        time.sleep(interval_seconds)

@square_bp.before_app_first_request
def start_background_polling():
    try:
        interval = int(os.environ.get("SQUARE_CUSTOMER_POLL_INTERVAL", "300"))
    except Exception:
        interval = 300
    t = threading.Thread(target=customer_polling_worker, args=(interval,), daemon=True)
    t.start()
    logger.info("Square customer polling thread started")
    return None

@square_bp.route('/webhooks/square', methods=['POST'])
def square_webhook_receiver():
    payload = {}
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    data = payload.get("data", {}) or {}
    obj = data.get("object", {}) or {}
    customer = obj.get("customer") or obj.get("customer_created") or payload.get("customer") or {}
    if not customer:
        for v in data.values():
            if isinstance(v, dict) and v.get("customer"):
                customer = v.get("customer")
                break

    if not customer:
        return jsonify({"message": "no customer in payload"}), 200

    try:
        linked = link_customer_to_local_user(customer)
        if linked:
            return jsonify({"message": "linked"}), 200
        else:
            return jsonify({"message": "no local match"}), 200
    except Exception:
        logger.exception("Webhook processing error")
        return jsonify({"error": "processing error"}), 500

@square_bp.route('/create-customer', methods=['POST'])
def create_customer():
    data = request.get_json() or {}
    try: 
        result = client.customers.create_customer(
            body={
                "given_name": data.get('given_name'),
                "family_name": data.get('family_name'),
                "email_address": data.get('email_address'),
                "phone_number": data.get('phone_number'),
                "address": data.get('address'),
                "reference_id": data.get('reference_id'),
                "note": data.get('note'),
                "idempotency_key": data.get('idempotency_key')
            }
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/list-customers', methods=['GET'])
def list_customers():
    try:
        result = client.customers.list_customers()
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/search-customers', methods=['POST'])
def search_customers():
    data = request.get_json() or {}
    try:
        query_filter = {}
        if data.get('email_address'):
            query_filter["email_address"] = {"exact": data.get('email_address')}
        if data.get('reference_id'):
            query_filter["reference_id"] = {"exact": data.get('reference_id')}
            
        result = client.customers.search_customers(
            body={
                "query": {
                    "filter": query_filter
                }
            }
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/create-card', methods=['POST'])
def create_card():
    data = request.get_json() or {}
    try:
        result = client.cards.create_card(
            body={
                "card":{
                    "cardholder_name": data.get('cardholder_name'),
                    "customer_id": data.get('customer_id'),
                    "exp_month": data.get('exp_month'),
                    "exp_year": data.get('exp_year'),
                    "reference_id": data.get('reference_id'),
                    "billing_address": data.get('billing_address')
                },
                "idempotency_key": data.get('idempotency_key'),
                "source_id": data.get('source_id')
            }
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/list-cards', methods=['GET'])
def list_cards():
    customer_id = request.args.get('customer_id')
    try:
        result = client.cards.list_cards(
            customer_id=customer_id
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/list-subscriptions', methods=['GET'])
def list_subscriptions():
    try:
        result = client.catalog.list_catalog(
            types='SUBSCRIPTION_PLAN'
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/enroll-subscription', methods=['POST'])
def enroll_customer():
    data = request.get_json() or {}
    try:
        result = client.subscriptions.create_subscription(
            body={
                "idempotency_key": data.get('idempotency_key'),
                "customer_id": data.get('customer_id'),
                "location_id": 'LQD9966CWR0XF',
                "card_id": data.get('card_id'),
                "plan_variation_id": data.get('plan_variant_id')
            }
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/cancel-subscription', methods=['POST'])
def cancel_subscription():
    data = request.get_json() or {}
    try:
        result = client.subscriptions.cancel_subscription(
            subscription_id=data.get('subscription_id')
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/search-subscriptions', methods=['POST'])
def search_subscriptions():
    data = request.get_json() or {}
    try:
        result = client.subscriptions.search_subscriptions(
            body={
                "query": {
                    "filter": {
                        "customer_ids": data.get('customer_ids', [])
                    }
                }
            }
        )
        if result.is_success():
            return jsonify(result.body), 200
        else:
            return jsonify({"errors": result.errors}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/create-catalog', methods=['POST'])
def delete_catalog():
    pass

@square_bp.route('/create-order', methods=['POST'])
def create_order():
    pass

@square_bp.route('/update-order', methods=['POST'])
def update_order():
    pass

@square_bp.route('/pay-order', methods=['POST'])
def pay_order():
    pass

@square_bp.route('/create-invoice', methods=['POST'])
def create_invoice():
    pass

@square_bp.route('/delete-invoice', methods=['POST'])
def delete_invoice():
    pass

@square_bp.route('/publish-invoice', methods=['POST'])
def publish_invoice():
    pass
