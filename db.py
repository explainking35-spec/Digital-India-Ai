from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['digitalindia']
users = db['users']
payments = db['payments']


async def create_trial(user_id, username):
    user = users.find_one({"user_id": user_id})
    if not user:
        expiry = datetime.utcnow() + timedelta(days=int(os.getenv('TRIAL_DAYS', 7)))
        users.insert_one({
            "user_id": user_id,
            "username": username,
            "expiry": expiry,
            "active": True,
            "trial": True
        })


async def is_active(user_id):
    user = users.find_one({"user_id": user_id})
    if not user:
        return False
    if datetime.utcnow() > user['expiry']:
        return False
    return True


async def add_payment_record(user_id, amount, utr, file_id):
    payment = {
        "user_id": user_id,
        "amount": amount,
        "utr": utr,
        "file_id": file_id,
        "status": "pending",
        "created": datetime.utcnow()
    }
    res = payments.insert_one(payment)
    return str(res.inserted_id)


def approve_payment(payment_id):
    payments.update_one({"_id": payment_id}, {"$set": {"status": "approved"}})
