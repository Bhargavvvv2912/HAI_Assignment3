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
class FinalResultsV5(db.Model):
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

# Create tables at startup (not just when someone visits '/')
with app.app_context():
    db.create_all()

# Global variables for data
versions_dict = {}

def get_data():
    """Safety function to load data only when needed"""
    global versions_dict
    if not versions_dict:
        for i in range(1, 7):
            path = f'data/Sarcasm_Study_Version_{i}.csv'
            if os.path.exists(path):
                versions_dict[i] = pd.read_csv(path)
    return versions_dict

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

    try:
        existing = FinalResultsV5.query.filter_by(uniqname=u_name).first()
        session['version'] = int(existing.version) if existing else random.randint(1, 6)
    except:
        session['version'] = random.randint(1, 6)

    session['current_trial'] = 0
    return redirect(url_for('task'))

@app.route('/task')
def task():
    data = get_data()
    v = session.get('version')
    idx = session.get('current_trial')

    if v not in data or idx >= 36:
        return redirect(url_for('complete'))

    df = data[v]
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

        data = get_data()
        df = data[v]

        start_time_str = session.get('start_time')
        duration = 0.0
        if start_time_str:
            duration = (datetime.datetime.now() - datetime.datetime.fromisoformat(start_time_str)).total_seconds()

        new_result = FinalResultsV5(
            uniqname=str(session.get('uniqname')),
            worker_id=str(session.get('worker_id')),
            condition=str(session.get('condition')),
            version=v,
            headline=str(df.iloc[idx]['input']),
            user_prediction=user_choice,
            ground_truth=int(df.iloc[idx]['ground_truth']),
            ai_used=ai_val,
            time_spent=round(duration, 2)
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

@app.route('/clear_bhargav_99')
def clear_db():
    try:
        # This will delete every row in your results table
        # If your table name is FinalData, use that. If it's FinalResultsV6, use that.
        num_deleted = db.session.query(FinalResultsV5).delete() 
        db.session.commit()
        return f"<h1>Database Cleared!</h1><p>Deleted {num_deleted} test entries. You are ready for the study!</p>"
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>"
    
@app.route('/export_bhargav_99')
def export_data():
    import io, csv
    from flask import Response
    results = FinalResultsV5.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Uniqname', 'WorkerID', 'Condition', 'Version', 'Headline', 'UserChoice', 'Truth', 'AI_Used', 'Time'])
    for r in results:
        writer.writerow([r.uniqname, r.worker_id, r.condition, r.version, r.headline,
                         r.user_prediction, r.ground_truth, r.ai_used, r.time_spent])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": "attachment; filename=results.csv"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)