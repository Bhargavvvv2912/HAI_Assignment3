from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import datetime
import uuid
import os

app = Flask(__name__)
app.secret_key = "umich_hai_study_secret"

# Load the 6 versions into memory
versions = {i: pd.read_csv(f'data/Sarcasm_Study_Version_{i}.csv') for i in range(1, 7)}

@app.route('/')
def index():
    # Capture condition and version from the URL
    session['condition'] = request.args.get('c', 'baseline')
    session['version'] = request.args.get('v', 1, type=int)
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_task():
    session['worker_id'] = request.form.get('worker_id')
    session['current_trial'] = 0
    return redirect(url_for('task'))

@app.route('/task')
def task():
    v = session.get('version')
    idx = session.get('current_trial')
    df = versions[v]
    
    if idx >= len(df):
        return redirect(url_for('complete'))

    trial_data = df.iloc[idx].to_dict()
    session['start_time'] = datetime.datetime.now().isoformat()
    
    return render_template('task.html', 
                           trial=trial_data, 
                           condition=session['condition'],
                           progress=f"{idx + 1} of {len(df)}")

@app.route('/submit', methods=['POST'])
def submit():
    user_choice = int(request.form.get('choice'))
    idx = session.get('current_trial')
    df = versions[session['version']]
    
    # Timing logic
    duration = (datetime.datetime.now() - datetime.datetime.fromisoformat(session['start_time'])).total_seconds()

    # Data to log (This is what gets you the bonus)
    log_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "worker_id": session.get('worker_id'),
        "condition": session.get('condition'),
        "version": session.get('version'),
        "headline": df.iloc[idx]['input'],
        "model_output": df.iloc[idx]['model_output'],
        "ai_confidence": df.iloc[idx]['ai_confidence'],
        "ground_truth": df.iloc[idx]['ground_truth'],
        "user_prediction": user_choice,
        "is_user_correct": 1 if user_choice == df.iloc[idx]['ground_truth'] else 0,
        "time_spent_seconds": round(duration, 2)
    }

    # Append to CSV
    log_df = pd.DataFrame([log_entry])
    log_df.to_csv('study_results.csv', mode='a', header=not os.path.exists('study_results.csv'), index=False)

    session['current_trial'] += 1
    return redirect(url_for('task'))

@app.route('/complete')
def complete():
    code = f"WIN-{str(uuid.uuid4())[:8].upper()}"
    return render_template('complete.html', completion_code=code)

if __name__ == "__main__":
    app.run(debug=True)