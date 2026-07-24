from pymongo import MongoClient

MONGO_URI = "mongodb+srv://dinesh7733_db_user:yD80Ojyk1mH5DBCP@cluster0.xtdqxe7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI)
    client.admin.command("ping")
    print("MongoDB Atlas Connected Successfully!")
except Exception as e:
    print("Connection Failed:", e)
