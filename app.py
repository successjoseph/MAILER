import os
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

@app.route('/')
def index():
    # Landing Page
    return render_template('index.html')

@app.route('/auth')
def auth():
    # Authentication Page
    return render_template('auth.html')

@app.route('/dashboard')
def dashboard():
    # Only access if logged in (add logic later)
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
