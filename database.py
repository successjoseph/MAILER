from google.oauth2 import id_token
from google.auth.transport import requests
import firebase_admin
from firebase_admin import firestore, credentials
import os

# Initialize Firebase Admin
# Note: You'll need the 'serviceAccountKey.json' from Firebase Console
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def verify_and_store_user(creds):
    """Verifies the Google ID and saves the Refresh Token to Firestore."""
    # Verify the ID token to get user details
    id_info = id_token.verify_oauth2_token(
        creds.id_token, requests.Request(), os.getenv("GOOGLE_CLIENT_ID")
    )
    
    uid = id_info['sub']
    email = id_info['email']
    
    user_data = {
        'uid': uid,
        'email': email,
        'name': id_info.get('name'),
        'refresh_token': creds.refresh_token, # This allows background polling
        'last_login': firestore.SERVER_TIMESTAMP
    }
    
    # Save/Update in Firestore Activity Logs/User Settings
    db.collection('users').document(uid).set(user_data, merge=True)
    return user_data

def save_user_manifesto(user_id, manifesto_text, duration):
    """Saves the AI instructions to the user's document."""
    doc_ref = db.collection('users').document(user_id)
    doc_ref.set({
        'manifesto': manifesto_text,
        'lookback_duration': duration
    }, merge=True)

def get_activity_logs(user_id):
    """Retrieves summaries of past AI actions."""
    logs = db.collection('users').document(user_id).collection('logs').stream()
    return [log.to_dict() for log in logs]

def add_activity_log(user_id, subject, recipient, action):
    """Logs an AI action to the user's Firestore subcollection."""
    log_data = {
        'subject': subject,
        'recipient': recipient,
        'action': action,
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    db.collection('users').document(user_id).collection('logs').add(log_data)

def update_user_tokens(user_id, tokens):
    """Securely stores Google Refresh Tokens in Firestore."""
    doc_ref = db.collection('users').document(user_id)
    doc_ref.set({
        'google_tokens': tokens
    }, merge=True)

def get_user_config(user_id):
    """Retrieves user manifesto and tokens for the background worker."""
    doc = db.collection('users').document(user_id).get()
    return doc.to_dict() if doc.exists else None