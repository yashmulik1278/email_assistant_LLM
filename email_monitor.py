# email_monitor.py
import os
import base64
import time
import re
import sqlite3 ### NEW ###: Import the SQLite3 library
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
DB_FILE = "emails.db" ### NEW ###: Define a constant for the database file

def get_gmail_service():
    """Authenticates with the Gmail API and returns a service object."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

### NEW ###
def save_email_to_db(msg_id, sender, subject, body, received_at):
    """Saves a single email's data into the SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # The 'OR IGNORE' ensures that if we try to insert a duplicate gmail_msg_id, it fails silently
        # which prevents crashing and duplicate entries.
        insert_query = """
        INSERT OR IGNORE INTO emails (gmail_msg_id, sender, subject, body, received_at)
        VALUES (?, ?, ?, ?, ?);
        """
        cursor.execute(insert_query, (msg_id, sender, subject, body, received_at.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        # The cursor.rowcount will be 1 if a new row was inserted, 0 otherwise.
        if cursor.rowcount > 0:
            print(f"Successfully saved email from {sender} to database.")
        else:
            print(f"Email from {sender} with ID {msg_id} already exists in database. Skipping.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")

def check_for_new_emails(service):
    """Checks for filtered unread emails, saves them to the DB, and marks them as read."""
    try:
        query = 'is:unread subject:(Support OR Query OR Request OR Help)'
        results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No new messages found.")
        else:
            print(f"Found {len(messages)} new message(s). Processing...")
            for message_info in messages:
                msg_id = message_info['id']
                msg = service.users().messages().get(userId='me', id=msg_id).execute()
                
                payload = msg['payload']
                headers = payload['headers']
                
                sender, subject, date_str = "N/A", "N/A", "N/A"
                for header in headers:
                    if header['name'] == 'From': sender = header['value']
                    if header['name'] == 'Subject': subject = header['value']
                    if header['name'] == 'Date': date_str = header['value']

                email_date = parsedate_to_datetime(date_str) if date_str != "N/A" else None

                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            encoded_body = part['body'].get('data', '')
                            body = base64.urlsafe_b64decode(encoded_body).decode('utf-8', errors='ignore')
                            break
                else:
                    encoded_body = payload['body'].get('data', '')
                    body = base64.urlsafe_b64decode(encoded_body).decode('utf-8', errors='ignore')
                
                # --- Print to console ---
                print("-" * 30)
                print(f"Processing email from: {sender}")
                print(f"Subject: {subject}")

                ### MODIFIED ###: Logic to save the email to the database
                if email_date:
                    save_email_to_db(msg_id, sender, subject, body, email_date)

                # Mark the email as read
                service.users().messages().modify(
                    userId='me', 
                    id=msg_id, 
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()

    except HttpError as error:
        print(f'An error occurred during email check: {error}')

def main():
    """Main function to authenticate and start the monitoring loop."""
    print("Starting email monitor... Press Ctrl+C to stop.")
        
    service = get_gmail_service()
    if not service:
        print("Failed to connect to Gmail. Exiting.")
        return

    try:
        while True:
            check_for_new_emails(service)
            print(f"Waiting for 60 seconds... (Last check: {time.strftime('%H:%M:%S')})")
            time.sleep(60) 
    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")

if __name__ == '__main__':
    main()