import os
import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # Change this in production
DB_FILE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            subject TEXT NOT NULL,
            purpose TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required!', 'error')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'error')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    if search_query:
        emails = conn.execute(
            'SELECT * FROM emails WHERE user_id = ? AND (subject LIKE ? OR purpose LIKE ?) ORDER BY created_at DESC',
            (session['user_id'], f'%{search_query}%', f'%{search_query}%')
        ).fetchall()
    else:
        emails = conn.execute(
            'SELECT * FROM emails WHERE user_id = ? ORDER BY created_at DESC', 
            (session['user_id'],)
        ).fetchall()
    conn.close()
    return render_template('dashboard.html', emails=emails, search_query=search_query)

@app.route('/generator')
def generator():
    return render_template('generator.html')

@app.route('/api/generate', methods=['POST'])
def generate_email():
    data = request.get_json()
    email_type = data.get('type')
    subject = data.get('subject')
    purpose = data.get('purpose')
    is_thread = data.get('is_thread', False)
    thread_type = data.get('thread_type', 'reply')
    
    # Mock AI Generation based on inputs
    if not is_thread:
        if not subject:
            subject = f"{email_type.replace('_', ' ').title()}: {purpose[:20]}..."
            
        content = f"Subject: {subject}\n\nDear [Name],\n\nI am writing to you regarding {purpose}. "
        
        if email_type == 'leave_request':
            content += "I would like to request leave for this purpose. I have ensured all my tasks are up to date.\n\nThank you for understanding."
        elif email_type == 'job_application':
            content += "I believe my skills and experience make me a strong candidate for this role. I have attached my resume for your review.\n\nI look forward to discussing this opportunity with you."
        else:
            content += "I hope we can discuss this further at your earliest convenience.\n\nPlease let me know if you need any additional information."
            
        content += "\n\nBest regards,\n[Your Name]"
    else:
        subject = f"Re: {subject}" if subject else f"Re: {purpose[:20]}..."
        if thread_type == 'reply':
            content = f"Subject: {subject}\n\nDear [Name],\n\nThank you for your previous email. Following up on {purpose}, I would like to add that we should proceed as discussed.\n\nBest regards,\n[Your Name]"
        elif thread_type == 'response':
            content = f"Subject: {subject}\n\nDear [Name],\n\nI have received your email regarding {purpose}. I have reviewed the details and agree with the proposed steps.\n\nBest regards,\n[Your Name]"
        else:
            content = f"Subject: {subject}\n\nDear [Name],\n\nHere is a complete summary of our conversation regarding {purpose}. Let's make sure we are all on the same page moving forward.\n\nBest regards,\n[Your Name]"

    # Save to database
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO emails (user_id, type, subject, purpose, content) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], email_type, subject, purpose, content)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'subject': subject,
        'content': content
    })

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
