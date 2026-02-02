import os
from groq import Groq
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.message import EmailMessage
import base64

import firebase_admin
from firebase_admin import firestore, credentials

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    if os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    else:
        raise Exception("Firebase credentials file 'serviceAccountKey.json' not found.")

db = firestore.client()

def get_user_config(user_id):
    """
    Retrieves the user configuration (manifesto, refresh token, etc.) from Firestore.
    """
    doc = db.collection('users').document(user_id).get()
    return doc.to_dict() if doc.exists else None

def add_activity_log(user_id, subject, recipient, action, draft_id=None):
    """
    Logs an email-related activity for a user in Firestore.
    """
    from datetime import datetime
    db.collection('activity_logs').add({
        'user_id': user_id,
        'subject': subject,
        'recipient': recipient,
        'action': action,
        'draft_id': draft_id,
        'timestamp': datetime.utcnow()
    })

load_dotenv()

def fetch_unread_emails(user_config):
    """
    Identifies unread threads via the Google API without persistent storage.
   
    """
    # Build credentials from the refresh token stored in Firestore
    creds = Credentials(
        token=None,  # Will be refreshed automatically
        refresh_token=user_config['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Query for unread messages
    duration = user_config.get('lookback_duration', '1')
    
    # 1. Aggressive Query Filter
    # Excludes common automated senders and subjects directly in the Gmail search
    blacklisted_terms = '-from:no-reply -from:noreply -subject:"Security alert" -subject:"Sign-in"'
    query = f'is:unread category:primary {blacklisted_terms} newer_than:{duration}d'
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages') or []
    
    threads = []
    for msg in messages[:10]:
        t_data = service.users().threads().get(userId='me', id=msg['threadId']).execute()
        msgs = t_data.get('messages', [])
        if not msgs: continue # Skip empty threads
        first_msg = msgs[0]
        payload = first_msg.get('payload', {})
        headers = first_msg['payload']['headers']
        
        # Checks if the email is marked as 'auto-generated' or has an unsubscribe link
        is_automated = any(
            h['name'].lower() in ['auto-submitted', 'list-unsubscribe', 'precedence'] 
            for h in headers
        )
        
        if is_automated:
            continue # Skip this mail, it's a bot or a newsletter
          # In engine.py -> fetch_unread_emails

        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "(No Subject)")
        
        threads.append({
            'id': msg['threadId'],
            'subject': subject,
            'body': get_full_body(first_msg['payload']) or first_msg['snippet'] # Fallback to snippet
        })
    return threads

def get_full_body(payload):
    """Recursively extracts plain text from Gmail payload."""
    if not payload: 
        return ""
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    parts = payload.get('parts') or []
    for part in parts:
        body = get_full_body(part)
        if body:
            return body
    return ""

def create_gmail_draft(user_config, thread_id, draft_body):
    """Creates a draft in the user's Gmail inbox."""

    refresh_token = user_config.get('refresh_token')
    if not refresh_token:
        raise ValueError("Missing refresh_token in user configuration.")
    
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    service = build('gmail', 'v1', credentials=creds)
    
    # Construct the raw RFC 2822 message
    message = EmailMessage()
    message.set_content(draft_body)
    # Note: We use the thread_id to keep it in the same conversation
    
    # Gmail API expects a base64url encoded string
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    draft_object = {
        'message': {
            'threadId': thread_id,
            'raw': raw_message
        }
    }
    try:
        draft = service.users().drafts().create(userId='me', body=draft_object).execute()
        return draft['id']
    except Exception as e:
        return None
    
def get_gmail_draft_content(user_config, draft_id):
    """Fetches draft body from Gmail on demand."""
    creds = Credentials(
        token=None, refresh_token=user_config['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"), client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    service = build('gmail', 'v1', credentials=creds)
    try:
        draft = service.users().drafts().get(userId='me', id=draft_id).execute()
        return get_full_body(draft['message']['payload']) or draft['message'].get('snippet', 'No content.')
    except:
        return "Error: Could not fetch draft."

def send_gmail_draft(user_config, draft_id):
    """Sends a specific Gmail draft."""
    creds = Credentials(
        token=None, refresh_token=user_config['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"), client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    service = build('gmail', 'v1', credentials=creds)
    try:
        service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
        return True
    except:
        return False
    
class MailerAI:
    def __init__(self):
        # Initialize the Groq client with the Llama-3.3-70b-versatile model
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    def draft_response(self, manifesto, email_content):
        """
        Uses the Manifesto with strict guardrails to generate professional replies.
        """
        system_prompt = (
            f"You are an AI Email Assistant acting on behalf of the user. "
            f"STRICTLY follow this Manifesto for persona and tone: {manifesto}\n\n"
            "RULES:\n"
            "1. DO NOT repeat or echo sensitive links (verification links, password resets) back to the sender.\n"
            "2. Do not explain the email to the sender; they sent it, they know what it says.\n"
            "3. Be concise and action-oriented. If a link was sent to you, just confirm you received it or will use it.\n"
            "4. Never use placeholders like '[Your Name]' if the Manifesto provides a name."
        )       
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": (
                        f"Here is an inbound email:\n---\n{email_content}\n---\n"
                        "Write a natural response based on the persona. If this is an automated "
                        "verification or notification, keep the reply extremely brief or "
                        "acknowledge the receipt without re-pasting the data."
                    )
                }
            ],
            temperature=0.7,
            max_tokens=1024
        )
        return completion.choices[0].message.content

    def generate_brief_report(self, activity_logs):
        """
        Synthesizes Firestore activity logs into a concise 'Absence Report'.
        """
        log_summary = "\n".join([f"- {log['subject']}: {log['action']}" for log in activity_logs])
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional coordinator. Summarize the following email activity logs into a brief, high-level executive report for the user."},
                {"role": "user", "content": f"Activity Logs:\n{log_summary}"}
            ],
            temperature=0.5
        )
        return completion.choices[0].message.content

    def ai_bubble_chat(self, user_query, recent_logs):
        """
        Interactive chat interface for users to query the AI regarding recent activities.
        """
        log_context = "\n".join([f"Thread: {log['subject']} | Status: {log['action']}" for log in recent_logs])
        system_message = (
            f"You are the MAILER AI Bubble. Use this context of recent activities to answer "
            f"user questions. Always respond using clean Markdown formatting.\n{log_context}"
        )

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_query}
            ],
            temperature=0.6
        )
        return completion.choices[0].message.content
    
def process_user_emails(user_id):
    """
    Background-safe function for the daemon:
    Fetch unread emails, generate AI drafts, and log activity.
    """
    user_config = get_user_config(user_id)
    if not user_config or not user_config.get('refresh_token'):
        return  # Skip users without a refresh token

    ai = MailerAI()
    try:
        threads = fetch_unread_emails(user_config)
        for thread in threads:
            draft_content = ai.draft_response(user_config.get('manifesto', ''), thread['body'])
            d_id = create_gmail_draft(user_config, thread['id'], draft_content)
            add_activity_log(
                user_id=user_id,
                subject=thread['subject'],
                recipient="Inbound Email",
                action="AI Draft Created",
                draft_id=d_id
            )
    except Exception as e:
        print(f"[{user_id}] Error processing emails: {e}")