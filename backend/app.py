from flask import Flask, send_from_directory
from flask_restx import Api
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

api.add_namespace(auth_ns, path="/api/auth")
api.add_namespace(user_ns, path="/api/user")
api.add_namespace(admin_ns, path="/api/admin")
api.add_namespace(transaction_ns, path="/api/transaction")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
