#!/usr/bin/env python3
"""
Postfeed runner — fetches Gmail, summarises, sends to Telegram.
Called by systemd timer or directly.
"""
import sys
import os
import datetime
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, LOG_FILE
from gmail_client import fetch_recent_emails
from summarizer import summarize_emails
from telegram_client import send_message, TelegramError

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)


def run():
    config = Config()
    now = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')

    try:
        logging.info("Postfeed starting run")
        emails = fetch_recent_emails(
            hours=config.interval_hours,
            max_results=config.max_emails,
        )
        logging.info(f"Fetched {len(emails)} emails")

        summary = summarize_emails(emails, config)
        send_message(config.telegram_token, config.telegram_chat_id, summary)

        config.set('last_run', now)
        config.set('last_status', f'OK — {len(emails)} emails processed')
        config.save()
        logging.info("Run complete")

    except TelegramError as e:
        msg = f'Telegram error: {e}'
        logging.error(msg)
        config.set('last_run', now)
        config.set('last_status', f'Error: {msg}')
        config.save()
        sys.exit(1)

    except Exception as e:
        msg = str(e)
        logging.error(f"Error: {msg}")
        config.set('last_run', now)
        config.set('last_status', f'Error: {msg}')
        config.save()
        sys.exit(1)


if __name__ == '__main__':
    run()
