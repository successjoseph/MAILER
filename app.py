import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from firebase_admin import firestore
from google_auth_oauthlib.flow import Flow
from database import get_user_config, verify_and_store_user, get_activity_logs, save_user_manifesto, add_activity_log
from engine import MailerAI, fetch_unread_emails, create_gmail_draft

# Load variables from .env
load_dotenv()

# Google OAuth2 Scopes - Needs Gmail modify + User Info
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Google OAuth2 Config
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")]
    }
}

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

@app.route('/')
def index():
    # Landing Page
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    if request.method == 'POST':
        # Grab data from the form
        manifesto = request.form.get('manifesto')
        duration = request.form.get('duration')
        user_id = session['user_id']
        
        # Save to Firestore via database.py
        save_user_manifesto(user_id, manifesto, duration)
        
        # Redirect to dashboard once configured
        return redirect(url_for('dashboard'))
        
    return render_template('setup.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    # Fetch the full config to get the manifesto
    user_config = get_user_config(session['user_id'])
    if not user_config:
        return redirect(url_for('setup'))
    
    # Extract info for the UI
    name = user_config.get('name', 'User')
    initial = name[0].upper() if name else 'U'
    manifesto = user_config.get('manifesto', 'No manifesto defined.')
    logs = get_activity_logs(session['user_id'])
    return render_template('dashboard.html', logs=logs, initial=initial, name=name, manifesto=manifesto)

@app.route('/auth')
def auth():
    # Authentication Page
    return render_template('auth.html')

@app.route('/login')
def login_page():
    return render_template('auth.html')

@app.route('/auth/google')
def auth_google():
    """Initiates the backend OAuth2 flow."""
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES
    )
    flow.redirect_uri = url_for('callback', _external=True)
    
    # access_type='offline' is critical for getting the Refresh Token
    auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    session['state'] = state
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Handles the redirect, saves tokens, and creates a session."""
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        state=session.get('state')
    )
    flow.redirect_uri = url_for('callback', _external=True)
    flow.fetch_token(authorization_response=request.url)
    
    creds = flow.credentials
    
    # Store user and tokens in Firestore via database.py
    user_info = verify_and_store_user(creds) 
    
    # Create the Python session
    session['user_id'] = user_info['uid']
    session['email'] = user_info['email']
    
    return redirect(url_for('setup'))


@app.route('/scan')
def scan_emails():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user_config = get_user_config(session['user_id'])
    ai = MailerAI()
    
    # 1. Fetch unread threads using your Refresh Token
    threads = fetch_unread_emails(user_config)
    
    for thread in threads:
        # 2. Draft response based on your Manifesto
        draft_content = ai.draft_response(user_config.get('manifesto'), thread['body'])
        create_gmail_draft(user_config, thread['id'], draft_content) 

        # 3. Log it so it shows up on the dashboard
        add_activity_log(
            session['user_id'], 
            thread['subject'], 
            "Inbound Email", 
            "AI Draft Created"
        )
        
    return redirect(url_for('dashboard'))

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    if 'user_id' not in session: return {"error": "Unauthorized"}, 401
    
    user_query = request.json.get('query')
    recent_logs = get_activity_logs(session['user_id'])[:10]
    
    ai = MailerAI()
    response = ai.ai_bubble_chat(user_query, recent_logs)
    return {"response": response}



if __name__ == '__main__':
    app.run(debug=True, port=5000)
