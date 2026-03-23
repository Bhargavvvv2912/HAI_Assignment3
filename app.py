from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "a_very_secret_key")

# Database Configuration
# In Render, add an Environment Variable called DATABASE_URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local_test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Result model (This replaces your CSV columns)
class StudyResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.String(100))
    condition = db.Column(db.String(20))
    version = db.Column(db.Integer)
    headline = db.Column(db.Text)
    user_prediction = db.Column(db.Integer)
    ground_truth = db.Column(db.Integer)
    time_spent = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Create the database tables
with app.app_context():
    db.create_all()

# --- Inside your /submit route ---
@app.route('/submit', methods=['POST'])
def submit():
    # ... (keep your existing logic to get user_choice and duration) ...
    
    # SAVE TO DATABASE INSTEAD OF CSV
    new_result = StudyResult(
        worker_id=session.get('worker_id'),
        condition=session.get('condition'),
        version=session.get('version'),
        headline=df.iloc[idx]['input'],
        user_prediction=user_choice,
        ground_truth=df.iloc[idx]['ground_truth'],
        time_spent=round(duration, 2)
    )
    db.session.add(new_result)
    db.session.commit()

    session['current_trial'] += 1
    return redirect(url_for('task'))