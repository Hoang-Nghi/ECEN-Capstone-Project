from flask import Blueprint, request, jsonify
from firebase_config import db
from firebase_admin import firestore

users_bp = Blueprint('users', __name__)

@users_bp.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    print("Received Data:", data)  # Debugging step
    user_ref = db.collection("users").document(data["user_id"])
    user_ref.set({
        "name": data["name"],
        "email": data["email"],
        "created_at": firestore.SERVER_TIMESTAMP
    })
    db.collection('users').add({
    'user_id': '12345',
    'name': 'John Doe',
    'email': 'john.doe@example.com'
})
    print("User added to Firestore!")  # Confirm it's saved
    return jsonify({"message": "User added successfully!"}), 201