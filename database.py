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
