import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin
# Note: You'll need the 'serviceAccountKey.json' from Firebase Console
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def save_user_manifesto(user_id, manifesto_text):
    """Saves the AI instructions to the user's document."""
    doc_ref = db.collection('users').document(user_id)
    doc_ref.set({
        'manifesto': manifesto_text
    }, merge=True)

def get_activity_logs(user_id):
    """Retrieves summaries of past AI actions."""
    logs = db.collection('users').document(user_id).collection('logs').stream()
    return [log.to_dict() for log in logs]

def save_google_refresh_token(user_id, refresh_token):
    """Saves the Google OAuth2 refresh token."""
    doc_ref = db.collection('users').document(user_id)
    doc_ref.set({
        'google_refresh_token': refresh_token
    }, merge=True)

def get_google_refresh_token(user_id):
    """Retrieves the Google OAuth2 refresh token."""
    doc_ref = db.collection('users').document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('google_refresh_token')
    return None