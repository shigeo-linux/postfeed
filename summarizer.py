import datetime
from api_client import APIClient, APIError

SUMMARY_SYSTEM = """You are an email assistant. You will be given a list of emails received in the last 12 hours. Produce a clear, concise digest summary.

Format your response exactly like this:

📬 <b>Email Digest</b> — {count} emails

For each important email, one line:
📧 <b>From:</b> [sender name] | <b>Subject:</b> [subject]
→ [one sentence summary of what the email is about]

At the end, add a brief overall summary line if there are patterns or priorities worth noting.

Skip newsletters, automated notifications, and spam unless they are important. Focus on emails requiring attention or containing useful information. Use HTML formatting as shown."""


def build_email_text(emails):
    parts = []
    for i, e in enumerate(emails, 1):
        parts.append(
            f"Email {i}:\n"
            f"From: {e['from']}\n"
            f"Subject: {e['subject']}\n"
            f"Date: {e['date']}\n"
            f"Content: {e['body'] or e['snippet']}\n"
        )
    return '\n---\n'.join(parts)


def summarize_emails(emails, config):
    if not emails:
        now = datetime.datetime.now().strftime('%H:%M on %d %b %Y')
        return f"📬 <b>Postfeed</b> — No new emails in the last {config.interval_hours} hours.\n🕐 Checked at {now}"

    api = APIClient(config)
    email_text = build_email_text(emails)
    system = SUMMARY_SYSTEM.replace('{count}', str(len(emails)))

    summary = api.complete(
        messages=[{'role': 'user', 'content': f"Here are the emails to summarise:\n\n{email_text}"}],
        system=system,
    )

    now = datetime.datetime.now().strftime('%H:%M on %d %b %Y')
    return f"{summary}\n\n🕐 <i>Sent by Postfeed at {now}</i>"
