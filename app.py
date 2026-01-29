import os
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

import requests
from database import save_google_refresh_token
from urllib.parse import urlencode

# Load variables from .env
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

@app.route('/')
def index():
    # Landing Page
    return render_template('index.html')

@app.route('/setup')
def setup():
    # Setup Page
    # Only access if logged in (add logic later)
    if 'user_id' not in session:
        return redirect(url_for('auth_google'))
    return render_template('setup.html')

@app.route('/auth')
def auth():
    # Authentication Page
    return render_template('auth.html')

@app.route('/dashboard')
def dashboard():
    # Dashboard Page
    # Only access if logged in (add logic later)
    if 'user_id' not in session:
        return redirect(url_for('auth_google'))
    return render_template('dashboard.html')

@app.route('/auth/google')
def auth_google():
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
    # SCOPE = "https://www.googleapis.com/auth/drive.file"
    SCOPES = [ 
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/userinfo.email"
    ]

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }

    from urllib.parse import urlencode, quote
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params, quote_via=quote)
    print("Google OAuth URL", url) # debug
    return redirect(url)

# @app.route('/auth/google/callback')
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error: No code provided", 400
    
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        return "Error: Failed to obtain tokens", 400
    
    tokens = response.json()
    refresh_token = tokens.get("refresh_token")
    id_token = tokens.get("id_token")

    if not refresh_token:
        return "Error: No refresh token received", 400
    
    # For demo purposes, using a fixed user_id
    user_id = id_token if id_token else "demo_user"

    save_google_refresh_token(user_id, refresh_token)
    session['user_id'] = user_id

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
