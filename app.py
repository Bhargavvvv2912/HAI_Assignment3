from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os, datetime, uuid, random, pandas as pd, traceback

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bhargav_sarcasm_study_2026")

# --- DATABASE CONFIG ---
uri = os.environ.get('DATABASE_URL', 'sqlite:///local_test.db')
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODEL ---
class FinalResultV3(db.Model): # New name to ensure a fresh, clean table
    id = db.Column(db.Integer, primary_key=True)
    uniqname = db.Column(db.String(50))
    worker_id = db.Column(db.String(100))
    condition = db.Column(db.String(20))
    version = db.Column(db.Integer)
    headline = db.Column(db.Text)
    user_prediction = db.Column(db.Integer)
    ground_truth = db.Column(db.Integer)
    ai_used = db.Column(db.Integer)
    time_spent = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# --- GLOBAL DATA ---
versions_dict = {}

# --- ONE-TIME STARTUP LOGIC ---
with app.app_context():
    print("--- STARTING APP BOOT ---")
    db.create_all()
    # Pre-load CSVs once during startup
    for i in range(1, 7):
        path = f'data/Sarcasm_Study_Version_{i}.csv'
        if os.path.exists(path):
            versions_dict[i] = pd.read_csv(path)
            print(f"Loaded Version {i} - {len(versions_dict[i])} rows")
    print("--- APP BOOT COMPLETE ---")

# --- ROUTES ---

@app.route('/')
def index():
    print(f"Index hit. Condition: {request.args.get('c')}")
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
    
    try:
        existing = FinalResultV3.query.filter_by(uniqname=u_name).first()
        session['version'] = int(existing.version) if existing else random.randint(1, 6)
    except:
        session['version'] = random.randint(1, 6)
        
    session['current_trial'] = 0
    return redirect(url_for('task'))

@app.route('/task')
def task():
    v = session.get('version')
    idx = session.get('current_trial')
    
    if v not in versions_dict or idx >= 36:
        return redirect(url_for('complete'))

    df = versions_dict[v]
    trial_data = df.iloc[idx].to_dict()
    session['start_time'] = datetime.datetime.now().isoformat()
    
    return render_template('task.html', 
                           trial=trial_data, 
                           condition=session['condition'],
                           progress=f"{idx + 1} of 36")

@app.route('/submit', methods=['POST'])
def submit():
    try:
        idx = int(session.get('current_trial', 0))
        v = int(session.get('version', 1))
        user_choice = int(request.form.get('choice', 0))
        ai_val = int(request.form.get('ai_used', 0))
        
        df = versions_dict[v]
        new_result = FinalResultV3(
            uniqname=str(session.get('uniqname')),
            worker_id=str(session.get('worker_id')),
            condition=str(session.get('condition')),
            version=v,
            headline=str(df.iloc[idx]['input']),
            user_prediction=user_choice,
            ground_truth=int(df.iloc[idx]['ground_truth']),
            ai_used=ai_val,
            time_spent=0.0 # Timer logic simplified for stability
        )
        db.session.add(new_result)
        db.session.commit()

        session['current_trial'] = idx + 1
        return redirect(url_for('task'))
    except Exception as e:
        return f"<h2>Submission Error</h2><pre>{traceback.format_exc()}</pre>"

@app.route('/complete')
def complete():
    u_name = session.get('uniqname', 'USER')
    code = f"SARCASM-{u_name[:3].upper()}-{str(uuid.uuid4())[:4].upper()}"
    return render_template('complete.html', completion_code=code)

@app.route('/export_bhargav_99')
def export_data():
    import io, csv
    from flask import Response
    results = FinalResultV3.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Uniqname', 'WorkerID', 'Condition', 'Version', 'Headline', 'UserChoice', 'Truth', 'AI_Used', 'Time'])
    for r in results:
        writer.writerow([r.uniqname, r.worker_id, r.condition, r.version, r.headline, r.user_prediction, r.ground_truth, r.ai_used, r.time_spent])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=results.csv"})

if __name__ == "__main__":
    # This block is for LOCAL TESTING only
    app.run(host='0.0.0.0', port=5000)