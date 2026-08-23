# MAILER

![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg) ![Model: Llama 3.3 70B](https://img.shields.io/badge/Model-Llama--3.3--70B-orange) ![Framework: Flask](https://img.shields.io/badge/Framework-Flask-green)

## About

MAILER is a Gmail-integrated AI email assistant: a user connects their Gmail account via Google OAuth2, writes a "Manifesto" (free-text instructions describing tone/persona/behavior) and picks a lookback window (24 hours / 3 days / 7 days), and the app fetches their unread primary-inbox emails from that window (filtering out obvious automated/no-reply/newsletter mail), asks Groq's `llama-3.3-70b-versatile` to draft a reply per the Manifesto, and saves each reply as a **Gmail draft** (it does not send automatically). A dashboard lists recent activity, shows AI-generated stats, and includes an "AI Bubble" chat widget that can answer questions about recent activity using Groq with the recent logs as context, plus an on-demand "Brief Report" that summarizes recent activity into an executive-style report. Only lightweight metadata (subject, action taken, draft ID) is stored in Firestore — full email bodies are fetched from Gmail on demand rather than persisted.

**Note on the repo's existing description:** the committed `README.md` describes MAILER as a FastAPI service using LangChain with an autonomous background worker that polls Gmail continuously. The actual code (`app.py`, `engine.py`) is a **Flask** app, calls the Groq SDK directly (no LangChain), and email scanning is **not** a background/scheduled process — it runs only when the user clicks "SCAN NOW" (`GET /scan`), which synchronously fetches, drafts, and logs before redirecting back to the dashboard. The existing README's "Organizational Roles" and "30-Day Sprint" sections describe a planned team/timeline rather than the actual (apparently solo) implementation. This README reflects what the code actually does.

## Table of Contents

- [About](#about)
- [Visuals](#visuals)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Security Notes](#security-notes)
- [Testing](#testing)
- [Author and License](#author-and-license)

## Visuals

`static/Mailer Hero.png` is a hero image used on the landing page (`templates/index.html`).

## Prerequisites

- Python 3 with the packages in `requirements.txt`: `flask==3.0.3`, `werkzeug==3.0.3`, `groq==0.5.0`, `httpx==0.27.2`, `gunicorn==22.0.0`, `python-dotenv==1.0.1`, `firebase_admin==6.5.0`, `google-auth-oauthlib==0.8.0`, `google-api-python-client==2.125.0`
- A Firebase project with Firestore enabled, and either a `serviceAccountKey.json` file (local dev) or a `FIREBASE_SERVICE_ACCOUNT_JSON` environment variable (production, per `database.py`)
- A Google Cloud OAuth2 client (Web application) with the Gmail API enabled, authorized for the `gmail.modify`, `openid`, `userinfo.email`, and `userinfo.profile` scopes
- A Groq API key

## Installation

```bash
git clone https://github.com/successjoseph/MAILER.git
cd MAILER
pip install -r requirements.txt
cp .env.example .env   # then fill in real values
```

## Configuration

Environment variables, per `.env.example`:

| Variable | Purpose |
|---|---|
| `FLASK_APP`, `FLASK_ENV` | Standard Flask config |
| `SECRET_KEY` | Flask session signing key |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google Cloud OAuth2 client credentials |
| `GOOGLE_REDIRECT_URI` | OAuth2 callback URL (defaults to `http://127.0.0.1:5000/callback` in `app.py` if unset) |
| `GROQ_API_KEY` | Groq API key used by `MailerAI` in `engine.py` |
| `FIREBASE_API_KEY`, `FIREBASE_PROJECT_ID`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_STORAGE_BUCKET`, `FIREBASE_APP_ID` | Firebase project identifiers |

`database.py` additionally reads `FIREBASE_SERVICE_ACCOUNT_JSON` (a JSON string, intended for production hosts like Render) or falls back to a local `serviceAccountKey.json` file — neither is listed in `.env.example` but both are required for Firebase Admin to initialize (the app raises an exception at import time if neither is available). `.gitignore` excludes `.env` and any `*.json` file, so no real credentials are committed.

## Usage

```bash
flask run
# or: python app.py
```

Flow: visit `/` (landing page) → `/login` (Continue with Google) → `/setup` to write a Manifesto and pick a lookback window (only reachable once logged in) → `/dashboard` shows recent activity, computed stats (triaged/drafts/pending), and an AI-generated brief report → click **SCAN NOW** (`/scan`) to fetch unread mail, generate drafts, and log the results → use the **AI Bubble** chat widget to ask questions about recent activity.

## API Documentation

Routes defined in `app.py` (session-based auth via Flask's signed cookie, not a public REST API):

| Method | Path | Description |
|---|---|---|
| GET | `/` | Landing page |
| GET | `/login`, `/auth` | Login/auth page |
| GET | `/auth/google` | Starts the Google OAuth2 consent flow |
| GET | `/callback` | OAuth2 callback; verifies the ID token and stores the refresh token in Firestore |
| GET/POST | `/setup` | View/save the user's Manifesto and lookback duration |
| GET | `/dashboard` | Renders activity logs, stats, and an AI-generated brief report |
| GET | `/scan` | Fetches unread Gmail threads, drafts AI replies, creates Gmail drafts, logs activity |
| POST | `/api/chat` | Body `{query}` — "AI Bubble" chat using the last 10 activity logs as context |
| GET | `/api/get_draft/<draft_id>` | Fetches a specific Gmail draft's content on demand |
| POST | `/api/send_draft` | Body `{draftId}` — sends a previously created Gmail draft |
| GET | `/logout` | Clears the session |

## Security Notes

- Login is exclusively via Google OAuth2 (`/auth/google` → `/callback`). An earlier `/auth/email` route accepted an email/password form but never actually checked the password, letting anyone log in as any known user's email; it had no corresponding UI (nothing in `templates/auth.html` posted to it) and was removed rather than patched, since the app's core feature (Gmail access) requires a refresh token that only the Google OAuth flow ever obtains.
- OAuth refresh tokens are stored directly in Firestore user documents (`database.py`); access to that Firestore project/database should be tightly restricted via security rules and IAM.

## Testing

No automated tests are currently included.

## Author and License

**Author:** [successjoseph](https://github.com/successjoseph)

**License:** Apache License 2.0 (see `LICENSE`). The project also attributes its use of Meta's Llama 3.3 model to the [Meta Llama 3.3 Community License](https://llama.meta.com/llama3/license/).
