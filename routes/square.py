import os
import threading
import time
import logging
import requests
import json
from flask import Blueprint, request, jsonify, render_template_string
from square import Square



square_bp = Blueprint('square', __name__)
logger = logging.getLogger("square_poll")

client = Square(
    token = os.environ.get("SQUARE_ACCESS_TOKEN", "")
)

def square_base_url():
    return "https://connect.squareup.com"

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
        from database.db import db
        from models.accounts import Client
    except Exception:
        try:
            from database.db import db
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

@square_bp.before_app_request
def start_background_polling():
    try:
        interval = int(os.environ.get("SQUARE_CUSTOMER_POLL_INTERVAL", "300"))
    except Exception:
        interval = 300
    t = threading.Thread(target=customer_polling_worker, args=(interval,), daemon=True)
    t.start()
    logger.info("Square customer polling thread started")
    return None

@square_bp.route('/payment-form')
def payment_form():
    return render_template_string('''
      <!DOCTYPE html>
      <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://web.squarecdn.com/v1/square.js"></script>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 20px;
            margin: 0;
            background-color: #f9fafb;
          }
          .form-group {
            margin-bottom: 16px;
          }
          label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #374151;
            margin-bottom: 6px;
          }
          input {
            width: 100%;
            padding: 12px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 16px;
            box-sizing: border-box;
          }
          input:focus {
            outline: none;
            border-color: #2563eb;
          }
          #card-container {
            margin: 16px 0;
            background: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: none;
          }
          #card-button {
            background-color: #2563eb;
            color: white;
            border: none;
            padding: 14px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            width: 100%;
            cursor: pointer;
            margin-top: 20px;
            display: none;
          }
          #card-button:disabled {
            background-color: #94a3b8;
            cursor: not-allowed;
          }
          #error-message {
            color: #ef4444;
            margin-top: 12px;
            font-size: 13px;
            padding: 12px;
            background-color: #fee2e2;
            border-radius: 6px;
            display: none;
          }
          #error-message.show {
            display: block;
          }
          #loading {
            text-align: center;
            color: #6b7280;
            padding: 20px;
            font-size: 14px;
          }
          .required {
            color: #ef4444;
          }
        </style>
      </head>
      <body>
        <div id="loading">Initializing payment form...</div>
        
        <form id="payment-form" style="display: none;">
          <div class="form-group">
            <label>Cardholder Name <span class="required">*</span></label>
            <input type="text" id="cardholder-name" placeholder="John Doe" required />
          </div>
          
          <div class="form-group">
            <label>Address Line 1 <span class="required">*</span></label>
            <input type="text" id="address-line-1" placeholder="123 Main St" required />
          </div>
          
          <div class="form-group">
            <label>Address Line 2</label>
            <input type="text" id="address-line-2" placeholder="Apt 4B (optional)" />
          </div>
          
          <div class="form-group">
            <label>City <span class="required">*</span></label>
            <input type="text" id="locality" placeholder="San Francisco" required />
          </div>
          
          <div class="form-group">
            <label>State/Province <span class="required">*</span></label>
            <input type="text" id="administrative-district" placeholder="CA" required maxlength="2" style="text-transform: uppercase;" />
          </div>
          
          <div class="form-group">
            <label>Postal Code <span class="required">*</span></label>
            <input type="text" id="postal-code" placeholder="94103" required />
          </div>
          
          <div class="form-group">
            <label>Country <span class="required">*</span></label>
            <input type="text" id="country" value="US" maxlength="2" style="text-transform: uppercase;" required />
          </div>
          
          <div class="form-group">
            <label>Card Details <span class="required">*</span></label>
            <div id="card-container"></div>
          </div>
          
          <button type="submit" id="card-button">Add Card</button>
        </form>
        
        <div id="error-message"></div>
        
        <script>
          (async function() {
            const errorDiv = document.getElementById('error-message');
            const loading = document.getElementById('loading');
            const paymentForm = document.getElementById('payment-form');
            const cardContainer = document.getElementById('card-container');
            const cardButton = document.getElementById('card-button');
            
            function showError(msg, details = '') {
              errorDiv.textContent = msg + (details ? '\\n\\n' + details : '');
              errorDiv.className = 'show';
              loading.style.display = 'none';
              if (window.ReactNativeWebView) {
                window.ReactNativeWebView.postMessage(JSON.stringify({ 
                  error: 'INIT_FAILED', 
                  message: msg, 
                  details 
                }));
              }
            }
            
            try {
              let attempts = 0;
              while (!window.Square && attempts < 50) {
                await new Promise(r => setTimeout(r, 100));
                attempts++;
              }
              
              if (!window.Square) throw new Error('Square SDK failed to load');
              
              loading.textContent = 'Connecting to Square...';
              const payments = Square.payments('sq0idp-_snKLfg8lpgNPIGtawYYUg', 'LQD9966CWR0XF');
              
              loading.textContent = 'Loading card form...';
              const card = await payments.card();
              await card.attach('#card-container');
              
              loading.style.display = 'none';
              paymentForm.style.display = 'block';
              cardContainer.style.display = 'block';
              cardButton.style.display = 'block';
              
              paymentForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                // Validate required fields
                const cardholderName = document.getElementById('cardholder-name').value.trim();
                const addressLine1 = document.getElementById('address-line-1').value.trim();
                const locality = document.getElementById('locality').value.trim();
                const adminDistrict = document.getElementById('administrative-district').value.trim();
                const postalCode = document.getElementById('postal-code').value.trim();
                const country = document.getElementById('country').value.trim();
                
                if (!cardholderName || !addressLine1 || !locality || !adminDistrict || !postalCode || !country) {
                  showError('Please fill in all required fields');
                  return;
                }
                
                cardButton.disabled = true;
                cardButton.textContent = 'Processing...';
                errorDiv.className = '';
                
                try {
                  const result = await card.tokenize();
                  if (result.status === 'OK') {
                    cardButton.textContent = 'Success!';
                    
                    // Send all data back to React Native
                    const cardData = {
                      nonce: result.token,
                      cardholder_name: cardholderName,
                      billing_address: {
                        address_line_1: addressLine1,
                        address_line_2: document.getElementById('address-line-2').value.trim() || undefined,
                        locality: locality,
                        administrative_district_level_1: adminDistrict.toUpperCase(),
                        postal_code: postalCode,
                        country: country.toUpperCase()
                      }
                    };
                    
                    if (window.ReactNativeWebView) {
                      window.ReactNativeWebView.postMessage(JSON.stringify(cardData));
                    }
                  } else {
                    showError('Failed to process card', result.errors?.map(e => e.message).join(', '));
                    cardButton.disabled = false;
                    cardButton.textContent = 'Add Card';
                  }
                } catch (e) {
                  showError('Error processing card', e.message);
                  cardButton.disabled = false;
                  cardButton.textContent = 'Add Card';
                }
              });
            } catch (error) {
              showError('Failed to initialize payment form', error.message);
            }
          })();
        </script>
      </body>
      </html>
    ''')

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
        url = f"{square_base_url()}/v2/customers"
        params = {
            "given_name": data.get("name"),
            "email_address": data.get("email"),
            "phone_number": data.get("phone"),
            "reference_id": data.get("user_id"),
            "note": data.get("note"),
            "idompotency_key": data.get("idempotency")
        }
        r = requests.post(url, headers=square_headers(), json=params, timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/list-customers', methods=['GET'])
def list_customers():
    pass

@square_bp.route('/search-customers', methods=['POST'])
def search_customers():
    data = request.get_json() or {}
    try:
        url = f"{square_base_url()}/v2/customers/search"
        params = {"query": {"filter": {"email_address": {"exact": data.get('email')}}}}
        r = requests.post(url, headers=square_headers(), json=params, timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/retrieve-customer')
def retrieve_customer():
    data = request.get_json() or {}
    try:
        url = f"{square_base_url()}/v2/customers{data.get('customer_id')}"
        r = requests.get(url, headers=square_headers(), timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/create-card', methods=['POST'])
def create_card():
    data = request.get_json() or {}
    try:
        url = f"{square_base_url()}/v2/cards"
        params={
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
        r = requests.post(url, headers=square_headers(), json=params, timeout=15)
        r.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/list-cards', methods=['GET'])
def list_cards():
    customer_id = request.args.get('customer_id')
    try:
        url = f"{square_base_url()}/v2/cards"
        params = {"customer_id": customer_id}
        r = requests.get(url, headers=square_headers(), params=params, timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/list-subscriptions', methods=['GET'])
def list_subscriptions():
    try:
        url = f"{square_base_url()}/v2/catalog/list"
        params = {"types": "subscription_PLAN"}
        
        r = requests.get(url, headers=square_headers(), params=params, timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/edit-subscription', methods=['POST'])
def edit_subscription():
    data = request.get_json() or {}

    try:
        url = f"{square_base_url()}/v2/catalog/object"

        params = {
            "idempotency_key": data.get("idempotency_key"),
            "object": {
                "id": data.get("id"),
                "type": "SUBSCRIPTION_PLAN",
                "subscription_plan_data": {
                    "name": data.get("name"),
                    "phases": [
                        {
                            "cadence": data.get("cadence"),
                            "ordinal": 0,
                            "pricing": {
                                "type": "STATIC",
                                "price_money": {
                                    "amount": int(data.get("amount")),
                                    "currency": "USD"
                                }
                            }
                        }
                    ]
                }
            }
        }

        r = requests.post(url, headers=square_headers(), json=params, timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), r.status_code

    except requests.exceptions.HTTPError as e:
        try:
            sq = e.response.json()
        except:
            sq = {"raw_error": e.response.text}

        print("SQUARE ERROR:", sq)

        return jsonify({
            "error": "square_error",
            "square_raw": sq
        }), 500

@square_bp.route('/enroll-subscription', methods=['POST'])
def enroll_customer():
    data = request.get_json() or {}
    try:
        url = f"{square_base_url()}/v2/subscriptions"
        params ={}
        r = requests.post(url, headers=square_headers(), json=params, timeout=15)
        r.raise_for_status()
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
        url = f"{square_base_url()}/v2/subscriptions/search"
        params = {"query": {"filter": {"customer_ids": [data.get('customer_ids')]}}}
        r = requests.post(url, headers=square_headers(), json=params, timeout=15)
        r.raise_for_status()
        print(f"Subscription Info:", json.dumps(r.json(), indent=2))
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@square_bp.route('/delete-catalog', methods=['POST'])
def delete_catalog():
    pass

@square_bp.route('/list-service', methods=['GET'])
def list_services():
    try:
        url = f"{square_base_url()}/v2/catalog/list"
        params = {"types": "ITEM"}
        r = request.get(url, headers=square_headers(), params=params, timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@square_bp.route('/retrieve-group', methods=['GET'])
def retrieve_group():
    data = request.get_json() or {}
    try:
        url = f"{square_base_url()}/v2/customers/groups/{data.get('group_id')}"
        r = requests.get(url, headers=square_headers(), timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@square_bp.route('/enroll-group', methods=['PUT'])
def enroll_group():
    data = request.get_json() or {}
    try:
        url = f"{square_base_url()}/v2/customers/{data.get('customer_id')}/groups/{data.get('group_id')}"
        r = requests.put(url, headers=square_headers(), timeout=15)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
