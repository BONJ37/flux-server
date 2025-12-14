import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# AUTO-DETECT DATABASE
# If on Render, use their Postgres DB. If local, use flux.db file.
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///flux.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    total_xp = db.Column(db.Integer, default=0)
    today_xp = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    def get_formatted_id(self):
        return str(self.id).zfill(6)

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET'])
def home():
    return "Flux Server is Live!"

@app.route('/api', methods=['POST'])
def handle_request():
    data = request.json
    action = data.get('action')
    
    # RECONNECT / REGISTER
    if action in ['reconnect', 'register']:
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        user = User.query.filter_by(email=email).first()

        if action == 'reconnect':
            if user:
                if user.username != username:
                    user.username = username
                    db.session.commit()
                return jsonify({"status":"success", "user_id":user.get_formatted_id(), "username":user.username, "email":user.email})
            return jsonify({"error":"user_not_found"})

        if action == 'register':
            if user: return jsonify({"error":"email_exists"})
            if User.query.filter_by(username=username).first(): return jsonify({"error":"name_taken"})
            new_user = User(username=username, email=email)
            db.session.add(new_user)
            db.session.commit()
            return jsonify({"status":"success", "user_id":new_user.get_formatted_id(), "username":new_user.username, "email":new_user.email})

    # UPDATE SCORE
    elif action == 'update':
        try: uid = int(data.get('user_id'))
        except: return jsonify({"error":"invalid_id"})
        user = User.query.get(uid)
        if user:
            user.total_xp = data.get('total_xp')
            user.today_xp = data.get('today_xp')
            user.last_active = datetime.utcnow()
            db.session.commit()
            return jsonify({"status":"updated"})
        return jsonify({"error":"user_not_found"})

    return jsonify({"error":"unknown_action"})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    users = User.query.order_by(User.today_xp.desc()).limit(50).all()
    result = []
    for u in users:
        result.append([u.username, u.total_xp, u.today_xp])
    return jsonify(result)