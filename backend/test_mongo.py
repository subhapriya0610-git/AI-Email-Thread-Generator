from pymongo import MongoClient

uri = "mongodb://admin:Subha%40Mongo2026@172.31.12.120:27017/aiemail?authSource=admin"

client = MongoClient(uri)

print(client.list_database_names())
print("MongoDB Connected Successfully!")
