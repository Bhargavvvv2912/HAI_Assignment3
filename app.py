from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import datetime
import uuid
import pandas as pd
import random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bhargav_sarcasm_study_2026")

# --- DATABASE CONFIGURATION ---
uri = os.environ.get('DATABASE_URL', 'sqlite:///local_test.db')
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODEL (Renamed to StudySubmission to fix 500 error) ---
class StudySubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uniqname = db.Column(db.String(50))
    worker_id = db.Column(db.String(100))
    condition = db.Column(db.String(20))
    version = db.Column(db.Integer)
    headline = db.Column(db.Text)
    user_prediction = db.Column(db.Integer)
    ground_truth = db.Column(db.Integer)
    time_spent = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Initialize tables
with app.app_context():
    # We keep drop_all() for ONE last push to ensure the new table is clean
    db.drop_all()
    db.create_all()

# --- DATA PRE-LOADING ---
versions_dict = {}
for i in range(1, 7):
    file_path = f'data/Sarcasm_Study_Version_{i}.csv'
    if os.path.exists(file_path):
        versions_dict[i] = pd.read_csv(file_path)
    else:
        print(f"CRITICAL ERROR: {file_path} not found!")

# --- ROUTES ---

@app.route('/')
def index():
    # This captures ?c=ai or ?c=baseline from the URL
    session['condition'] = request.args.get('c', 'baseline')
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_task():
    u_name = request.form.get('uniqname', '').strip().lower()
    w_id = request.form.get('worker_id', '').strip().upper()
    
    if not u_name or not w_id:
        return redirect(url_for('index'))
    
    session['uniqname'] = u_name
    session['worker_id'] = w_id
    
    # Check DB using the NEW model name
    existing = StudySubmission.query.filter_by(uniqname=u_name).first()
    
    if existing:
        assigned_version = existing.version
    else:
        assigned_version = random.randint(1, 6)
    
    session['version'] = assigned_version
    session['current_trial'] = 0
    return redirect(url_for('task'))

@app.route('/task')
def task():
    v = session.get('version')
    idx = session.get('current_trial')
    
    if v not in versions_dict or idx >= len(versions_dict[v]):
        return redirect(url_for('complete'))

    df = versions_dict[v]
    trial_data = df.iloc[idx].to_dict()
    session['start_time'] = datetime.datetime.now().isoformat()
    
    return render_template('task.html', 
                           trial=trial_data, 
                           condition=session['condition'],
                           progress=f"{idx + 1} of {len(df)}")

@app.route('/submit', methods=['POST'])
def submit():
    # Ensure this matches name="choice" in task.html
    user_choice = int(request.form.get('choice', 0))
    idx = session.get('current_trial')
    v = session.get('version')
    df = versions_dict[v]
    
    start = datetime.datetime.fromisoformat(session['start_time'])
    duration = (datetime.datetime.now() - start).total_seconds()

    # SAVE TO DATABASE using the NEW model name
    new_result = StudySubmission(
        uniqname=session.get('uniqname'),
        worker_id=session.get('worker_id'),
        condition=session.get('condition'),
        version=v,
        headline=df.iloc[idx]['input'],
        user_prediction=user_choice,
        ground_truth=df.iloc[idx]['ground_truth'],
        time_spent=round(duration, 2)
    )
    db.session.add(new_result)
    db.session.commit()

    session['current_trial'] += 1
    return redirect(url_for('task'))

@app.route('/complete')
def complete():
    code = f"SARCASM-{session.get('uniqname')[:3].upper()}-{str(uuid.uuid4())[:4].upper()}"
    return render_template('complete.html', completion_code=code)

@app.route('/export_bhargav_99')
def export_data():
    import io, csv
    from flask import Response
    results = StudySubmission.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Uniqname', 'WorkerID', 'Condition', 'Version', 'Headline', 'UserChoice', 'Truth', 'Time'])
    for r in results:
        writer.writerow([r.uniqname, r.worker_id, r.condition, r.version, r.headline, r.user_prediction, r.ground_truth, r.time_spent])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=study_results.csv"})

if __name__ == "__main__":
    app.run(debug=True)