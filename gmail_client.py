import os
import base64
import datetime
from config import CONFIG_DIR, TOKEN_FILE, CREDENTIALS_FILE

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_gmail_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not os.path.exists(CREDENTIALS_FILE):
        raise RuntimeError(
            f"Gmail credentials not found.\n"
            f"Please download credentials.json from Google Cloud Console\n"
            f"and save it to: {CREDENTIALS_FILE}\n\n"
            f"See Settings → Gmail Setup for instructions."
        )

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def fetch_recent_emails(hours=12, max_results=20):
    """Fetch emails received in the last N hours."""
    service = get_gmail_service()

    since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    query = f'after:{int(since.timestamp())}'

    result = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results,
    ).execute()

    messages = result.get('messages', [])
    emails = []

    for msg in messages:
        try:
            full = service.users().messages().get(
                userId='me', id=msg['id'], format='full'
            ).execute()
            email = _parse_message(full)
            if email:
                emails.append(email)
        except Exception:
            continue

    return emails


def _parse_message(msg):
    headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
    subject = headers.get('Subject', '(no subject)')
    sender = headers.get('From', 'Unknown')
    date = headers.get('Date', '')
    snippet = msg.get('snippet', '')

    body = _extract_body(msg.get('payload', {}))

    return {
        'subject': subject,
        'from': sender,
        'date': date,
        'snippet': snippet,
        'body': body[:2000] if body else snippet,
    }


def _extract_body(payload):
    mime = payload.get('mimeType', '')
    if mime == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
    elif mime.startswith('multipart/'):
        for part in payload.get('parts', []):
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
    return ''
