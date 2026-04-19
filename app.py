import os
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from firebase_admin import firestore
from google_auth_oauthlib.flow import Flow
from database import get_user_config, verify_and_store_user, get_activity_logs, save_user_manifesto, add_activity_log
from engine import MailerAI, fetch_unread_emails, create_gmail_draft, get_gmail_draft_content, send_gmail_draft
from werkzeug.middleware.proxy_fix import ProxyFix

# Load variables from .env
load_dotenv()

# Google OAuth2 Scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Dynamic Redirect URI from Environment for local/prod flexibility
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/callback")

GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI]
    }
}

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# Tell Flask it is behind a secure reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enforce strict, production-ready session security
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    if request.method == 'POST':
        manifesto = request.form.get('manifesto')
        duration = request.form.get('duration')
        user_id = session['user_id']
        
        save_user_manifesto(user_id, manifesto, duration)
        return redirect(url_for('dashboard'))
    
    # Pre-fill settings from Firebase
    user_config = get_user_config(session['user_id'])
    return render_template('setup.html', config=user_config or {})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user_config = get_user_config(session['user_id'])
    if not user_config:
        return redirect(url_for('setup'))
    
    # Handle "Load More" logic via query param
    limit = int(request.args.get('limit', 5))
    logs = get_activity_logs(session['user_id'], limit=limit)
    
    # Stats Calculation (Fetch a larger set to calculate totals)
    stat_logs = get_activity_logs(session['user_id'], limit=100)
    stats = {
        'triaged': len(stat_logs),
        'drafts': len([l for l in stat_logs if "Draft" in l.get('action', '')]),
        'pending': len([l for l in stat_logs if "Inbound" in l.get('action', '')])
    }

    ai = MailerAI()
    report = ai.generate_brief_report(stat_logs) if stat_logs else "No activity to summarize yet."
    
    name = user_config.get('name', 'User')
    initial = name[0].upper() if name else 'U'
    manifesto = user_config.get('manifesto', 'No manifesto defined.')    
    return render_template('dashboard.html', logs=logs, initial=initial, name=name, manifesto=manifesto, stats=stats, current_limit=limit, report=report)

@app.route('/auth')
def auth():
    return render_template('auth.html')

@app.route('/login')
def login_page():
    return render_template('auth.html')

@app.route('/auth/google')
def auth_google():
    flow = Flow.from_client_config(GOOGLE_CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = url_for('callback', _external=True)
    
    # Logic Clause: Check if we already have a refresh token for this user
    # Note: Since 'user_id' might not be in session during a fresh login, 
    # we usually default to 'select_account' unless we know they need a token.
    # To be safe, we can use 'select_account' but provide a "Re-authorize" button 
    # on the dashboard if things break.
    
    prompt_type = 'select_account'
    
    # If you have the user's email or ID in session from a previous step:
    if 'user_id' in session:
        user_config = get_user_config(session['user_id'])
        if not user_config or not user_config.get('refresh_token'):
            prompt_type = 'consent'

    auth_url, state = flow.authorization_url(
        access_type='offline', 
        prompt=prompt_type
    )
    session['state'] = state
    return redirect(auth_url)

@app.route('/auth/email', methods=['POST'])
def auth_email():
    email = request.form.get('email')
    password = request.form.get('password') # In prod, use hashing!
    
    from database import db
    user_ref = db.collection('users').where('email', '==', email).limit(1).get()
    
    if not user_ref:
        uid = f"local_{email.split('@')[0]}"
        user_info = {'uid': uid, 'email': email, 'name': email.split('@')[0]}
        db.collection('users').document(uid).set(user_info)
        session['user_id'] = uid
    else:
        session['user_id'] = user_ref[0].id
        
    session['email'] = email
    return redirect(url_for('dashboard'))

@app.route('/callback')
def callback():
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        state=session.get('state')
    )
    flow.redirect_uri = url_for('callback', _external=True)
    flow.fetch_token(authorization_response=request.url)
    
    user_info = verify_and_store_user(flow.credentials) 
    session['user_id'] = user_info['uid']
    session['email'] = user_info['email']
    
    return redirect(url_for('dashboard'))

# MAILER/app.py

@app.route('/scan')
def scan_emails():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user_config = get_user_config(session['user_id'])
    
    # ERROR PREVENTION: Logic clause to check token existence
    if not user_config or not user_config.get('refresh_token'):
        # Redirect to auth with forced consent because token is missing
        return redirect(url_for('auth_google'))
    
    ai = MailerAI()
    try:
        threads = fetch_unread_emails(user_config)
        for thread in threads:
            draft_content = ai.draft_response(user_config.get('manifesto'), thread['body'])
            d_id = create_gmail_draft(user_config, thread['id'], draft_content) 
            
            if d_id:
                add_activity_log(
                    session['user_id'], 
                    thread['subject'], 
                    "Inbound Email", 
                    "AI Draft Created",
                    draft_id=d_id
                )
    except Exception as e:
        # Catch the RefreshError here if the token is revoked/invalid
        return f"Authentication error: {str(e)}. Please try logging in again.", 401
        
    return redirect(url_for('dashboard'))

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    if 'user_id' not in session: 
        return {"error": "Unauthorized"}, 401
    
    user_query = request.json.get('query')
    # Use context of last 10 logs for the AI bubble
    recent_logs = get_activity_logs(session['user_id'], limit=10)
    
    ai = MailerAI()
    response = ai.ai_bubble_chat(user_query, recent_logs)
    return {"response": response}

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/get_draft/<draft_id>')
def api_get_draft(draft_id):
    if 'user_id' not in session: return {"error": "Auth required"}, 401
    user_config = get_user_config(session['user_id'])
    # Corrected: Call function directly
    content = get_gmail_draft_content(user_config, draft_id) 
    return {"content": content}

@app.route('/api/send_draft', methods=['POST'])
def api_send_draft():
    if 'user_id' not in session: return {"error": "Auth required"}, 401
    draft_id = request.json.get('draftId')
    user_config = get_user_config(session['user_id'])
    from engine import send_gmail_draft
    if send_gmail_draft(user_config, draft_id):
        return {"success": True}
    return {"error": "Send failed"}, 500

if __name__ == '__main__':
    app.run(debug=True)
