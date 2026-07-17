import os
import sqlite3
import datetime
import secrets
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

DB_FILE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Create emails table
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
    # Create sessions table for token authentication
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database on startup
init_db()

# Decorator to enforce token auth
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                
        if not token:
            return jsonify({'success': False, 'error': 'Authentication token is missing!'}), 401
            
        conn = get_db_connection()
        session_row = conn.execute('SELECT * FROM sessions WHERE token = ?', (token,)).fetchone()
        if not session_row:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid or expired token!'}), 401
            
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session_row['user_id'],)).fetchone()
        conn.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found!'}), 401
            
        return f(user, *args, **kwargs)
    return decorated

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required!'}), 400
        
    hashed_password = generate_password_hash(password)
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        return jsonify({'success': True, 'message': 'Registration successful!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Username already exists!'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required!'}), 400
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    
    if user and check_password_hash(user['password'], password):
        # Generate token
        token = secrets.token_hex(32)
        # Store session
        conn.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user['id']))
        conn.commit()
        conn.close()
        return jsonify({
            'success': True,
            'token': token,
            'username': user['username']
        }), 200
    else:
        conn.close()
        return jsonify({'success': False, 'error': 'Invalid username or password!'}), 401

@app.route('/api/logout', methods=['POST'])
@token_required
def logout(current_user):
    # Extract token
    auth_header = request.headers['Authorization']
    token = auth_header.split(' ')[1]
    
    conn = get_db_connection()
    conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Logged out successfully!'}), 200

@app.route('/api/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    if search_query:
        emails = conn.execute(
            'SELECT * FROM emails WHERE user_id = ? AND (subject LIKE ? OR purpose LIKE ?) ORDER BY created_at DESC',
            (current_user['id'], f'%{search_query}%', f'%{search_query}%')
        ).fetchall()
    else:
        emails = conn.execute(
            'SELECT * FROM emails WHERE user_id = ? ORDER BY created_at DESC', 
            (current_user['id'],)
        ).fetchall()
    conn.close()
    
    emails_list = []
    for email in emails:
        emails_list.append({
            'id': email['id'],
            'type': email['type'],
            'subject': email['subject'],
            'purpose': email['purpose'],
            'content': email['content'],
            'created_at': email['created_at']
        })
        
    return jsonify({
        'success': True,
        'username': current_user['username'],
        'emails': emails_list
    }), 200

@app.route('/api/generate', methods=['POST'])
@token_required
def generate_email(current_user):
    data = request.get_json() or {}
    email_type = data.get('type')
    subject = data.get('subject')
    purpose = data.get('purpose')
    is_thread = data.get('is_thread', False)
    thread_type = data.get('thread_type', 'reply')
    
    if not purpose:
        return jsonify({'success': False, 'error': 'Purpose is required!'}), 400
        
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
        (current_user['id'], email_type, subject, purpose, content)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'subject': subject,
        'content': content
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
