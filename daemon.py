# import time
# from engine import get_user_config, fetch_unread_emails, add_activity_log, create_gmail_draft
# from googleapiclient.errors import HttpError

# CHECK_INTERVAL = 15 * 60  # 15 minutes in seconds

# def run_daemon():
#     print("MAILER daemon started...")
#     while True:
#         try:
#             # Get all users from Firestore
#             users = get_all_users()  # We'll define this below
#             for user in users:
#                 user_id = user['uid']
#                 user_config = get_user_config(user_id)
#                 if not user_config or 'refresh_token' not in user_config:
#                     continue

#                 # Fetch unread emails for this user
#                 try:
#                     threads = fetch_unread_emails(user_config)
#                 except HttpError as e:
#                     print(f"[{user_id}] Gmail API error: {e}")
#                     continue

#                 for thread in threads:
#                     # Log each email processed
#                     add_activity_log(
#                         user_id=user_id,
#                         subject=thread.get('subject', 'No Subject'),
#                         recipient=user_config.get('email', 'Unknown'),
#                         action="Identified inbound email",
#                         draft_id=None
#                     )
#                     # Optional: You could generate drafts here if needed
#                     draft_id = create_gmail_draft(user_config, thread['id'], "AI draft placeholder")
#                     add_activity_log(user_id, thread.get('subject', ''), user_config.get('email', ''), "Draft Created", draft_id)

#             print("Cycle complete. Waiting 15 minutes...")
#             time.sleep(CHECK_INTERVAL)

#         except Exception as e:
#             print(f"Daemon error: {e}")
#             time.sleep(60)  # Wait 1 minute on error and retry


# # Helper to get all users from Firestore
# def get_all_users():
#     from engine import db  # Import Firestore client from engine.py
#     users_ref = db.collection('users')
#     docs = users_ref.stream()
#     return [doc.to_dict() for doc in docs if doc.exists]

# if __name__ == "__main__":
#     run_daemon()

from app import scan_emails  # Import the scan function
import time

CHECK_INTERVAL = 1 * 60  # 15 minutes

def run_daemon():
    print("MAILER background daemon started...")
    while True:
        try:
            scan_emails()  # This will perform the scan exactly like clicking "SCAN NOW"
            print("Scan complete. Sleeping 15 minutes...")
        except Exception as e:
            print(f"Daemon error: {e}. Retrying in 1 minute...")
            time.sleep(60)
            continue
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_daemon()

# import time
# from engine import process_user_emails
# from database import db

# CHECK_INTERVAL = 15 * 60  # 15 minutes

# def run_daemon():
#     print("MAILER background daemon started...")
#     while True:
#         try:
#             users = db.collection('users').stream()
#             for doc in users:
#                 user_id = doc.id
#                 process_user_emails(user_id)

#             print("Cycle complete. Sleeping 15 minutes...")
#         except Exception as e:
#             print(f"Daemon error: {e}. Retrying in 1 minute...")
#             time.sleep(60)
#             continue

#         time.sleep(CHECK_INTERVAL)


# if __name__ == "__main__":
#     run_daemon()
