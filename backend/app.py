<<<<<<< HEAD
from flask import Flask, send_from_directory
from flask_restx import Api
=======
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
import datetime
import secrets
from functools import wraps
from flask import Flask, request, jsonify
>>>>>>> b76b18d (Update backend app.py)
from flask_cors import CORS
from pymongo import MongoClient
import os

app = Flask(__name__)
CORS(app)

MONGO_URI = "mongodb+srv://dinesh7733_db_user:yD80Ojyk1mH5DBCP@cluster0.xtdqxe7.mongodb.net/bankdb?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["bankdb"]

FRONTEND_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend')
)

@app.route('/')
def home():
    try:
        client.admin.command("ping")
        return "Backend Running Successfully (MongoDB Atlas)"
    except Exception as e:
        return f"MongoDB Connection Failed: {e}"

@app.route('/<path:path>')
def frontend_files(path):
    return send_from_directory(FRONTEND_FOLDER, path)

api = Api(
    app,
    title="Bank API",
    version="1.0",
    doc="/docs"
)

from auth_swagger import auth_ns
from user_swagger import user_ns
from admin_swagger import admin_ns
from transaction_swagger import transaction_ns

<<<<<<< HEAD
api.add_namespace(auth_ns, path="/api/auth")
api.add_namespace(user_ns, path="/api/user")
api.add_namespace(admin_ns, path="/api/admin")
api.add_namespace(transaction_ns, path="/api/transaction")
=======
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
@app.route("/")
def home():
    return "Backend is Running Successfully!"
>>>>>>> b76b18d (Update backend app.py)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
