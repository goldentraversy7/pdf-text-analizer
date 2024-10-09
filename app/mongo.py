from pymongo import MongoClient
from flask import current_app

def get_db():
    client = MongoClient(current_app.config['MONGO_URI'])
    return client.get_default_database()

def get_user_info(email, type):
    db = get_db()
    collection = db['users']
    try:
        user = collection.find_one({'email': email, 'type': type})
        return user
    except Exception as e:
        return "Something went wrong"
    
def update_user_info(email, type, update_data):
    db = get_db()
    collection = db['users']
    query_filter = {"email": email, 'type': type}
    update_operation = {}
    update_operation['$set'] = update_data
    collection.update_one(query_filter, update_operation)
