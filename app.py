from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os, datetime, uuid, random, pandas as pd, traceback

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bhargav_sarcasm_study_2026")

# --- DATABASE CONFIGURATION ---
uri = os.environ.get('DATABASE_URL', 'sqlite:///local_test.db')
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODEL ---
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

# Initialize tables (Safe: no drop_all)
with app.app_context():
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
    
    existing = StudySubmission.query.filter_by(uniqname=u_name).first()
    session['version'] = existing.version if existing else random.randint(1, 6)
    session['current_trial'] = 0
    return redirect(url_for('task'))

@app.route('/task')
def task():
    v = session.get('version')
    idx = session.get('current_trial')
    
    # UPDATE: We end the study at 36 trials regardless of CSV length
    # This keeps your accuracy and time metrics consistent for A3-2
    if v not in versions_dict or idx >= 36 or idx >= len(versions_dict[v]):
        return redirect(url_for('complete'))

    df = versions_dict[v]
    trial_data = df.iloc[idx].to_dict()
    session['start_time'] = datetime.datetime.now().isoformat()
    
    return render_template('task.html', 
                           trial=trial_data, 
                           condition=session['condition'],
                           progress=f"{idx + 1} of 36") # Always shows 'of 36'

@app.route('/submit', methods=['POST'])
def submit():
    try:
        idx = session.get('current_trial')
        v = session.get('version')

        if idx is None or v is None:
            return redirect(url_for('index'))

        idx, v = int(idx), int(v)
        user_choice = int(request.form.get('choice', 0))
        df = versions_dict[v]
        
        headline_text = str(df.iloc[idx]['input'])
        truth_value = int(df.iloc[idx]['ground_truth'])
        
        start_time_str = session.get('start_time')
        duration = 0.0
        if start_time_str:
            duration = (datetime.datetime.now() - datetime.datetime.fromisoformat(start_time_str)).total_seconds()

        new_result = StudySubmission(
            uniqname=str(session.get('uniqname')),
            worker_id=str(session.get('worker_id')),
            condition=str(session.get('condition')),
            version=int(v),
            headline=headline_text,
            user_prediction=int(user_choice),
            ground_truth=int(truth_value),
            time_spent=float(round(duration, 2))
        )
        db.session.add(new_result)
        db.session.commit()

        session['current_trial'] = idx + 1
        return redirect(url_for('task'))
    
    except Exception as e:
        return f"<h2>Submission Error</h2><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"

@app.route('/complete')
def complete():
    # Final check for uniqname to avoid errors on page refresh
    u_name = session.get('uniqname', 'USER')
    code = f"SARCASM-{u_name[:3].upper()}-{str(uuid.uuid4())[:4].upper()}"
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