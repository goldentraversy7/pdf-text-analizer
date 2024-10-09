
from app.mongo import get_db

def get_users():
    db = get_db()
    users_collection = db['users']
    result = users_collection.find_one({'name' : 'almart'})
    print(result)
    return result

def get_constdf_file_id():
    db = get_db()
    collection = db['settings']
    settings = collection.find_one()
    file_id = settings['constdf_file_id']
    return file_id