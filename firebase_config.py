import firebase_admin
from firebase_admin import credentials, firestore

# Load Firebase credentials
cred = credentials.Certificate(r"C:\Users\HoangNghi\ECEN403_Capstone_Project\ecen403-capstone-project-firebase-adminsdk-fbsvc-05e85e2afe.json")  # Update this path
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()
