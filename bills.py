from flask import Blueprint, request, jsonify
from firebase_config import db  # Ensure firebase_config is correctly imported
from firebase_admin import firestore

bills_bp = Blueprint('bills', __name__)

@bills_bp.route('/add_bill', methods=['POST'])
def add_bill():
    data = request.json
    bill_ref = db.collection("bills").document()
    bill_ref.set({
        "user_id": data["user_id"],
        "amount": data["amount"],
        "due_date": data["due_date"],
        "status": data["status"],
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return jsonify({"message": "Bill added successfully!"}), 201
