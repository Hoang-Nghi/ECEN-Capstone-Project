from flask import Blueprint, request, jsonify
from firebase_config import db
from firebase_admin import firestore

receipts_bp = Blueprint('receipts', __name__)

@receipts_bp.route('/add_receipt', methods=['POST'])
def add_receipt():
    data = request.json
    receipt_ref = db.collection("receipts").document()
    receipt_ref.set({
        "user_id": data["user_id"],
        "store_name": data["store_name"],
        "total_amount": data["total_amount"],
        "items": data["items"],
        "date": firestore.SERVER_TIMESTAMP
    })
    return jsonify({"message": "Receipt added!"}), 201
