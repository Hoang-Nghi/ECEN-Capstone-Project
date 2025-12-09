from flask import Blueprint, jsonify
from ml.train import train_and_save_model

ml_bp = Blueprint('ml', __name__)

@ml_bp.route('/train', methods=['POST'])
def train_model():
    success = train_and_save_model()
    return jsonify({"status": "success" if success else "failed"}), 200 if success else 500