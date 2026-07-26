import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))


class FakeCollection:
    def __init__(self):
        self.docs = []

    def create_index(self, *args, **kwargs):
        return None

    def insert_one(self, document):
        document = dict(document)
        document.setdefault("_id", f"fake-id-{len(self.docs) + 1}")
        self.docs.append(document)
        return type("InsertResult", (), {"inserted_id": document["_id"]})()

    def find_one(self, query):
        username = query.get("username")
        for document in self.docs:
            if document.get("username") == username:
                return document
        return None


class FakeDatabase:
    def __init__(self):
        self.users = FakeCollection()
        self.emails = FakeCollection()

    def __getitem__(self, name):
        if name == "users":
            return self.users
        if name == "emails":
            return self.emails
        raise KeyError(name)


class FakeMongoClient:
    def __init__(self, *args, **kwargs):
        self.db = FakeDatabase()

    def __getitem__(self, name):
        return self.db

    def admin_command(self, *args, **kwargs):
        return {"ok": 1}


with patch("pymongo.MongoClient", FakeMongoClient):
    import app as app_module


class AuthFlowTests(unittest.TestCase):
    def setUp(self):
        self.fake_users = app_module.users_collection
        self.fake_emails = app_module.emails_collection
        self.patcher = patch.object(app_module, "users_collection", self.fake_users)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        app_module.app.testing = True
        self.client = app_module.app.test_client()

    def test_register_and_login_return_frontend_ready_payload(self):
        register_response = self.client.post(
            "/api/register",
            json={"username": "alice", "password": "secret"},
        )
        self.assertEqual(register_response.status_code, 201)
        register_data = register_response.get_json()
        self.assertTrue(register_data["success"])
        self.assertEqual(register_data["username"], "alice")

        login_response = self.client.post(
            "/api/login",
            json={"username": "alice", "password": "secret"},
        )
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.get_json()
        self.assertTrue(login_data["success"])
        self.assertEqual(login_data["username"], "alice")
        self.assertTrue(login_data["token"])


if __name__ == "__main__":
    unittest.main()
