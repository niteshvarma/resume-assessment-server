import firebase_admin
from firebase_admin import credentials, firestore
import logging

# Path to your service account JSON file
SERVICE_ACCOUNT_PATH = "genfoundry/firebase-config.json"

# Initialize Firebase app (only once)
# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
    logging.debug("Firebase initialized")

# Initialize Firestore database
db = firestore.client()
