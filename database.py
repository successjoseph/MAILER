import json
import os
import firebase_admin
from firebase_admin import firestore, credentials

# Initialize Firebase Admin
if not firebase_admin._apps:
    # 1. Try to get JSON string from Environment Variable (Best for Render/Production)
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    if service_account_json:
        cred_dict = json.loads(service_account_json)
        cred = credentials.Certificate(cred_dict)
    elif os.path.exists("serviceAccountKey.json"):
        # 2. Fallback to local file (Best for Development)
        cred = credentials.Certificate("serviceAccountKey.json")
    else:
        raise Exception("Firebase credentials missing from Environment Variable and File.")

    firebase_admin.initialize_app(cred)

db = firestore.client()

def verify_and_store_user(creds):
    """Verifies the Google ID and saves the Refresh Token to Firestore."""
    from google.oauth2 import id_token
    from google.auth.transport import requests
    
    id_info = id_token.verify_oauth2_token(
        creds.id_token, requests.Request(), os.getenv("GOOGLE_CLIENT_ID")
    )
    
    uid = id_info['sub']
    email = id_info['email']
    
    user_data = {
        'uid': uid,
        'email': email,
        'name': id_info.get('name'),
        'refresh_token': creds.refresh_token,
        'last_login': firestore.SERVER_TIMESTAMP
    }
    
    db.collection('users').document(uid).set(user_data, merge=True)
    return user_data

def save_user_manifesto(user_id, manifesto_text, duration, name=None):
    """Saves the AI instructions and profile updates to the user's document."""
    doc_ref = db.collection('users').document(user_id)
    update_data = {
        'manifesto': manifesto_text,
        'lookback_duration': duration
    }
    if name:
        update_data['name'] = name
    doc_ref.set(update_data, merge=True)

def get_activity_logs(user_id, limit=5):
    """Retrieves summaries of past AI actions with sorting and limits."""
    logs_ref = db.collection('users').document(user_id).collection('logs')
    # Order by newest first
    query = logs_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
    return [log.to_dict() for log in query.stream()]

def add_activity_log(user_id, subject, recipient, action, draft_id=None):
    """Logs an AI action with the Gmail Draft ID. Content is fetched from Gmail on demand."""
    log_data = {
        'subject': subject,
        'recipient': recipient,
        'action': action,
        'draft_id': draft_id, # The only identifier we need
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    db.collection('users').document(user_id).collection('logs').add(log_data)

def get_user_config(user_id):
    """Retrieves user manifesto and tokens for the background worker."""
    doc = db.collection('users').document(user_id).get()
    return doc.to_dict() if doc.exists else None

def update_user_tokens(user_id, tokens):
    """Securely stores Google Refresh Tokens in Firestore."""
    doc_ref = db.collection('users').document(user_id)
    doc_ref.set({'google_tokens': tokens}, merge=True)