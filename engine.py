import os
from groq import Groq
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage
import base64

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
    messages = results.get('messages', [])
    
    threads = []
    for msg in messages[:10]: # Increased limit, but we filter more strictly now
        t_data = service.users().threads().get(userId='me', id=msg['threadId']).execute()
        first_msg = t_data['messages'][0]
        headers = first_msg['payload']['headers']
        
        # 2. Header-Level Stopper
        # Checks if the email is marked as 'auto-generated' or has an unsubscribe link
        is_automated = any(
            h['name'].lower() in ['auto-submitted', 'list-unsubscribe', 'precedence'] 
            for h in headers
        )
        
        if is_automated:
            continue # Skip this mail, it's a bot or a newsletter
            
        subject = next(h['value'] for h in headers if h['name'] == 'Subject')
        
        threads.append({
            'id': msg['threadId'],
            'subject': subject,
            'body': first_msg['snippet']
        })
    return threads

def create_gmail_draft(user_config, thread_id, draft_body):
    """Creates a draft in the user's Gmail inbox."""
    creds = Credentials(
        token=None,
        refresh_token=user_config['refresh_token'],
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
        service.users().drafts().create(userId='me', body=draft_object).execute()
        return True
    except Exception as e:
        print(f"Draft Error: {e}")
        return False

class MailerAI:
    def __init__(self):
        # Initialize the Groq client with the Llama-3.3-70b-versatile model
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    def draft_response(self, manifesto, email_content):
        """
        Uses the Manifesto to generate a contextual email reply.
        """
        system_prompt = f"You are an AI Email Assistant. Strictly follow this Manifesto for persona, tone, and logic: {manifesto}"
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Draft a response to this email:\n\n{email_content}"}
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
        system_message = f"You are the MAILER AI Bubble. Use this context of recent activities to answer user questions:\n{log_context}"

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_query}
            ],
            temperature=0.6
        )
        return completion.choices[0].message.content