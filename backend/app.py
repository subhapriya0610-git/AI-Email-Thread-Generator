import base64
import datetime
import hashlib
import hmac
import json
import os
from functools import wraps
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "aiemail")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[MONGO_DB_NAME]
users_collection = db["users"]
emails_collection = db["emails"]

users_collection.create_index("username", unique=True)
emails_collection.create_index([("user_id", 1), ("created_at", -1)])


def base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def encode_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    encoded_header = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = base64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_jwt(token: str) -> dict[str, Any] | None:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        actual_signature = base64url_decode(signature_b64)
        expected_signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()

        if not hmac.compare_digest(actual_signature, expected_signature):
            return None

        payload = json.loads(base64url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")

        if exp is not None and datetime.datetime.utcnow().timestamp() > exp:
            return None

        return payload
    except Exception:
        return None


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.config["JSON_SORT_KEYS"] = False

    def http_error(message: str, status_code: int = 400) -> tuple[dict[str, Any], int]:
        return {"success": False, "error": message}, status_code

    def require_json() -> dict[str, Any] | tuple[dict[str, Any], int]:
        payload = request.get_json(silent=True)
        if payload is None:
            return http_error("Request body must be JSON.", 400)
        return payload

    def verify_token() -> dict[str, Any] | tuple[dict[str, Any], int] | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_jwt(token)
        if payload is None:
            return None

        sub = payload.get("sub")
        if not isinstance(sub, str):
            return None

        try:
            return {"payload": payload, "sub_id": ObjectId(sub)}
        except Exception:
            return None

    def token_required(view: Any) -> Any:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            token_data = verify_token()
            if token_data is None:
                return http_error("Invalid or expired token.", 401)

            user = users_collection.find_one({"_id": token_data["sub_id"]})
            if user is None:
                return http_error("User not found.", 401)

            return view(user, *args, **kwargs)

        return wrapped

    @app.route("/", methods=["GET"])
    def health_check() -> tuple[dict[str, Any], int]:
        try:
            client.admin.command("ping")
            return {"success": True, "message": "AI Email Thread Generator backend is running."}, 200
        except Exception as error:
            return http_error(f"Database connection failed: {error}", 503)

    @app.route("/api/register", methods=["POST"])
    def register() -> tuple[dict[str, Any], int]:
        payload = require_json()
        if isinstance(payload, tuple):
            return payload

        username = (payload.get("username") or "").strip()
        password = payload.get("password")

        if not username or not password:
            return http_error("Username and password are required.", 400)

        hashed_password = generate_password_hash(password)
        user_document = {
            "username": username,
            "password": hashed_password,
            "created_at": datetime.datetime.utcnow(),
        }

        try:
            result = users_collection.insert_one(user_document)
            user_id = result.inserted_id
        except DuplicateKeyError:
            return http_error("A user with this username already exists.", 409)
        except Exception as error:
            return http_error(f"Unable to create user: {error}", 500)

        return {
            "success": True,
            "id": str(user_id),
            "username": username,
        }, 201

    @app.route("/api/login", methods=["POST"])
    def login() -> tuple[dict[str, Any], int]:
        payload = require_json()
        if isinstance(payload, tuple):
            return payload

        username = (payload.get("username") or "").strip()
        password = payload.get("password")

        if not username or not password:
            return http_error("Username and password are required.", 400)

        user = users_collection.find_one({"username": username})
        if user is None or not check_password_hash(user["password"], password):
            return http_error("Invalid username or password.", 401)

        now = datetime.datetime.utcnow()
        token_payload = {
            "sub": str(user["_id"]),
            "username": user["username"],
            "iat": int(now.timestamp()),
            "exp": int((now + datetime.timedelta(seconds=JWT_EXPIRATION_SECONDS)).timestamp()),
        }
        access_token = encode_jwt(token_payload)

        return {
            "success": True,
            "token": access_token,
            "username": user["username"],
            "expires_in": JWT_EXPIRATION_SECONDS,
            "user": {
                "id": str(user["_id"]),
                "username": user["username"],
            },
        }, 200

    def build_email_text(email_type: str, subject: str, purpose: str, tone: str, thread_mode: bool) -> tuple[str, str]:
        core_subject = subject.strip() or f"{email_type.replace('_', ' ').title()} Request"
        greeting = "Dear [Recipient],"
        closing = "Best regards,\n[Your Name]"
        tone_intro = {
            "professional": "I hope this message finds you well.",
            "friendly": "I hope you are doing well and having a great day.",
            "concise": "I will keep this message brief.",
        }.get(tone, "I am reaching out regarding the following matter.")

        if thread_mode:
            body = (
                f"{greeting}\n\nThank you for your recent message about {purpose}. "
                f"{tone_intro} I would like to continue the conversation and provide the next steps. "
                f"Please let me know if you have any questions or if there is anything else I can share.\n\n{closing}"
            )
        else:
            body = (
                f"{greeting}\n\n{tone_intro} I am writing to you regarding {purpose}. "
                f"{'' if email_type == 'general' else 'In particular, I would like to address the requested topic and explain how it aligns with our goals. '}"
                f"I appreciate your attention to this matter and look forward to your response.\n\n{closing}"
            )

        return core_subject, body

    @app.route("/api/generate", methods=["POST"])
    @token_required
    def generate_email(current_user: dict[str, Any]) -> tuple[dict[str, Any], int]:
        payload = require_json()
        if isinstance(payload, tuple):
            return payload

        email_type = (payload.get("type") or "general").strip().lower()
        subject = (payload.get("subject") or "").strip()
        purpose = (payload.get("purpose") or "").strip()
        tone = (payload.get("tone") or "professional").strip().lower()
        thread_mode = bool(payload.get("thread", False))

        if not purpose:
            return http_error("Purpose is required to generate an email.", 400)

        generated_subject, generated_body = build_email_text(email_type, subject, purpose, tone, thread_mode)
        email_document = {
            "user_id": current_user["_id"],
            "type": email_type,
            "subject": generated_subject,
            "purpose": purpose,
            "tone": tone,
            "thread": thread_mode,
            "body": generated_body,
            "created_at": datetime.datetime.utcnow(),
        }

        result = emails_collection.insert_one(email_document)

        return {
            "success": True,
            "data": {
                "id": str(result.inserted_id),
                "subject": generated_subject,
                "body": generated_body,
            },
        }, 201

    @app.route("/api/history", methods=["GET"])
    @token_required
    def email_history(current_user: dict[str, Any]) -> tuple[dict[str, Any], int]:
        limit = min(int(request.args.get("limit", "25")), 100)
        page = max(int(request.args.get("page", "1")), 1)
        skip = (page - 1) * limit

        cursor = emails_collection.find({"user_id": current_user["_id"]}).sort("created_at", -1).skip(skip).limit(limit)
        history = [
            {
                "id": str(item["_id"]),
                "type": item.get("type", "general"),
                "subject": item.get("subject", ""),
                "purpose": item.get("purpose", ""),
                "tone": item.get("tone", "professional"),
                "thread": bool(item.get("thread", False)),
                "body": item.get("body", ""),
                "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
            }
            for item in cursor
        ]

        return {"success": True, "data": {"emails": history, "page": page, "limit": limit}}, 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
