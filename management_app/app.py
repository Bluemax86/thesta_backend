import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from flask_socketiolask import Flask, request, session, jsonify
from flask_cors import CORS
import bcrypt

# Manually load .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
with open(env_path, 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

from db import (create_user, get_user_by_email, update_last_logged_in,
                get_reservations, get_total_reservations, get_total_revenue,
                get_revenue_by_type)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_HTTPONLY'] = True
CORS(app, supports_credentials=True, origins=[os.getenv("FRONTEND_URL")],
     methods=["GET", "POST", "OPTIONS"],  # Allow these methods
     allow_headers=["Content-Type", "Authorization"])  # Allow these headers

def is_authenticated():
    return session.get('logged_in', False)

@app.route('/')
def index():
    return jsonify({"status": "API is running"}), 200

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json(silent=True)  # Use silent=True to avoid errors
        email = data.get('email')
        password = data.get('password')
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            create_user(email, password_hash, 'admin')
            user = get_user_by_email(email, 'admin')
            session['logged_in'] = True
            session['user_id'] = user[0]
            session.modified = True  # Force session modification
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
        user = get_user_by_email(email, 'admin')
        print('User:', user)  # Debug log
        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            session['logged_in'] = True
            session['user_id'] = user[0]
            session.modified = True  # Force session modification
            print('Session after login:', session)  # Debug log
            update_last_logged_in(email)
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"error": "Method not allowed"}), 405

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return jsonify({"message": "Logout successful"}), 200

@app.route('/dashboard')
def dashboard():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401

    reservations = get_reservations()
    total_reservations = get_total_reservations()
    total_revenue = get_total_revenue()
    revenue_by_type = get_revenue_by_type()

    return jsonify({
        "reservations": [
            {
                "reservation_id": r[0],
                "customer": f"{r[1]} {r[2]}",
                "product_name": r[3],
                "check_in_date": str(r[4]),
                "check_out_date": str(r[5]),
                "total_cost": float(r[6])
            } for r in reservations
        ],
        "total_reservations": total_reservations,
        "total_revenue": float(total_revenue),
        "revenue_by_type": [
            {"type": rt[0], "revenue": float(rt[1])} for rt in revenue_by_type
        ]
    })

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5001))  # Default to 5001 if not set
    app.run(debug=True, port=port)