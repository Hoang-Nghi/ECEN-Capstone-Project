from flask import Blueprint, request, jsonify
from firebase_config import db  # Ensure firebase_config is correctly imported
from firebase_admin import firestore

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/add_expense', methods=['POST'])
def add_expense():
    data = request.json
    expense_ref = db.collection("expenses").document()
    expense_ref.set({
        "user_id": data["user_id"],
        "amount": data["amount"],
        "category": data["category"],
        "date": firestore.SERVER_TIMESTAMP
    })
    return jsonify({"message": "Expense added!"}), 201
