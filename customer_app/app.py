import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, session, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import bcrypt
from dotenv import load_dotenv
from db import (get_products_by_type, create_reservation, get_reservation_by_id,
                get_customer_id_by_user_id, create_user, create_customer,
                get_user_by_email, update_last_logged_in)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_HTTPONLY'] = True
CORS(app, supports_credentials=True, origins=[os.getenv("FRONTEND_URL")],
     methods=["GET", "POST", "OPTIONS"],  # Allow these methods
     allow_headers=["Content-Type", "Authorization"])  # Allow these headers

# Simple login check
def is_authenticated():
    return session.get('logged_in', False)

# Simple AI parsing
def parse_inquiry(inquiry):
    inquiry = inquiry.lower()
    product_type = None
    check_in_date = None
    nights = 1

    if "cabin" in inquiry:
        product_type = "Cabin"
    elif "spa" in inquiry:
        product_type = "Spa"
    elif "activity" in inquiry or "activities" in inquiry:
        product_type = "Activities"

    if "april" in inquiry:
        check_in_date = "2025-04-10"
    words = inquiry.split()
    for i, word in enumerate(words):
        if word.isdigit() and i + 1 < len(words) and "night" in words[i + 1]:
            nights = int(word)
            break

    return product_type, check_in_date, nights

@app.route('/')
def home():
    return jsonify({"status": "API is running"}), 200

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        data = request.get_json(silent=True)
        if data is None:
          return jsonify({"error": "Invalid JSON payload"}), 400
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone = data.get('phone')
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            user_id = create_user(email, password_hash, 'customer')
            create_customer(user_id, first_name, last_name, email, phone)
            session['logged_in'] = True
            session['user_id'] = user_id
            return jsonify({"message": "Signup successful"}), 200
        except Exception as e:
            return jsonify({"error": "Email already exists"}), 400
    return jsonify({"error": "Method not allowed"}), 405

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user = get_user_by_email(email, 'customer')
        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            session['logged_in'] = True
            session['user_id'] = user[0]
            update_last_logged_in(email)
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"error": "Method not allowed"}), 405

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    return jsonify({"message": "Logout successful"}), 200

@app.route('/chat', methods=['POST'])
def chat():
    #if not is_authenticated():
    #    return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON payload"}), 400
    inquiry = data.get('inquiry')
    product_type, check_in_date, nights = parse_inquiry(inquiry)
    products = get_products_by_type(product_type, check_in_date is not None)

    results = []
    for product in products:
        product_id, product_name, unit_price, fixed_price, reservable, default_image_url, description = product
        unit_price = float(unit_price)
        total_cost = unit_price * nights if fixed_price else unit_price * nights * 1.2
        results.append({
            'product_id': product_id,
            'product_name': product_name,
            'description': description,
            'total_cost': total_cost,
            'nights': nights,
            'check_in_date': check_in_date or "Not specified",
            'image_url': default_image_url or '/static/images/placeholder.jpg'
        })

    return jsonify({"inquiry": inquiry, "results": results})

@app.route('/book', methods=['POST'])
def book():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON payload"}), 400
    product_id = data.get('product_id')
    check_in_date = data.get('check_in_date')
    nights = data.get('nights')
    total_cost = data.get('total_cost')

    if check_in_date == "Not specified":
        check_in_date = datetime.now().date()
    else:
        check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d').date()
    check_out_date = check_in_date + timedelta(days=nights)

    user_id = session['user_id']
    customer_id = get_customer_id_by_user_id(user_id)

    reservation_id = create_reservation(customer_id, product_id, check_in_date, check_out_date, total_cost)
    reservation = get_reservation_by_id(reservation_id)

    return jsonify({
        "reservation_id": reservation[0],
        "customer": f"{reservation[1]} {reservation[2]}",
        "product_name": reservation[3],
        "check_in_date": str(reservation[4]),
        "check_out_date": str(reservation[5]),
        "total_cost": float(reservation[6])
    })

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))  # Default to 5000 if not set
    app.run(debug=True, port=port)