import os
import subprocess
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from config import Config, CREDENTIALS_FILE, LOG_FILE
from api_client import APIClient
from telegram_client import send_message, test_connection, TelegramError

STYLE_PATH = os.path.join(os.path.dirname(__file__), 'style.css')

MODELS = [
    'anthropic/claude-3.5-sonnet',
    'anthropic/claude-3-opus',
    'openai/gpt-4o',
    'openai/gpt-4o-mini',
    'google/gemini-pro-1.5',
]


def _load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(STYLE_PATH)
    except Exception:
        pass
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Postfeed')
        self.set_default_size(500, 560)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_icon_name('postfeed')
        _load_css()

        self.config = Config()
        self._busy = False
        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title('Postfeed')
        header.set_subtitle('Gmail → Telegram digest')
        self.set_titlebar(header)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_border_width(20)
        main.pack_start(content, True, True, 0)

        # ── Status card ──────────────────────────────────────────
        status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        status_card.get_style_context().add_class('status-card')

        status_title = Gtk.Label(label='Status', xalign=0)
        status_title.get_style_context().add_class('section-title')
        status_card.pack_start(status_title, False, False, 0)

        self._status_label = Gtk.Label(label='Not yet run', xalign=0)
        self._status_label.get_style_context().add_class('status-pending')
        status_card.pack_start(self._status_label, False, False, 0)

        self._last_run_label = Gtk.Label(label='', xalign=0)
        self._last_run_label.get_style_context().add_class('meta-label')
        status_card.pack_start(self._last_run_label, False, False, 0)

        self._next_run_label = Gtk.Label(label='', xalign=0)
        self._next_run_label.get_style_context().add_class('meta-label')
        status_card.pack_start(self._next_run_label, False, False, 0)

        content.pack_start(status_card, False, False, 0)

        # ── Run now ───────────────────────────────────────────────
        run_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._run_btn = Gtk.Button(label='Run Now')
        self._run_btn.get_style_context().add_class('action-btn')
        self._run_btn.connect('clicked', self._on_run_now)
        run_row.pack_start(self._run_btn, False, False, 0)
        self._spinner = Gtk.Spinner()
        run_row.pack_start(self._spinner, False, False, 0)
        self._run_label = Gtk.Label(label='', xalign=0)
        self._run_label.get_style_context().add_class('meta-label')
        run_row.pack_start(self._run_label, False, False, 0)
        content.pack_start(run_row, False, False, 0)

        sep = Gtk.Separator()
        content.pack_start(sep, False, False, 0)

        # ── Settings ──────────────────────────────────────────────
        settings_title = Gtk.Label(label='Settings', xalign=0)
        settings_title.get_style_context().add_class('section-title')
        content.pack_start(settings_title, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        # OpenRouter API key
        grid.attach(Gtk.Label(label='OpenRouter API Key:', xalign=1), 0, 0, 1, 1)
        self._api_key_entry = Gtk.Entry()
        self._api_key_entry.set_hexpand(True)
        self._api_key_entry.set_visibility(False)
        self._api_key_entry.set_text(self.config.api_key)
        self._api_key_entry.set_placeholder_text('sk-or-...')
        grid.attach(self._api_key_entry, 1, 0, 1, 1)

        # Model
        grid.attach(Gtk.Label(label='Model:', xalign=1), 0, 1, 1, 1)
        self._model_combo = Gtk.ComboBoxText()
        for m in MODELS:
            self._model_combo.append(m, m)
        active = self.config.model
        self._model_combo.set_active_id(active if active in MODELS else MODELS[0])
        grid.attach(self._model_combo, 1, 1, 1, 1)

        # Telegram token
        grid.attach(Gtk.Label(label='Telegram Token:', xalign=1), 0, 2, 1, 1)
        self._tg_token_entry = Gtk.Entry()
        self._tg_token_entry.set_hexpand(True)
        self._tg_token_entry.set_visibility(False)
        self._tg_token_entry.set_text(self.config.telegram_token)
        self._tg_token_entry.set_placeholder_text('123456789:ABCdef...')
        grid.attach(self._tg_token_entry, 1, 2, 1, 1)

        # Telegram chat ID
        grid.attach(Gtk.Label(label='Telegram Chat ID:', xalign=1), 0, 3, 1, 1)
        self._tg_chat_entry = Gtk.Entry()
        self._tg_chat_entry.set_text(self.config.telegram_chat_id)
        self._tg_chat_entry.set_placeholder_text('e.g. 123456789')
        grid.attach(self._tg_chat_entry, 1, 3, 1, 1)

        # Interval
        grid.attach(Gtk.Label(label='Send every (hours):', xalign=1), 0, 4, 1, 1)
        self._interval_spin = Gtk.SpinButton.new_with_range(1, 24, 1)
        self._interval_spin.set_value(self.config.interval_hours)
        grid.attach(self._interval_spin, 1, 4, 1, 1)

        # Max emails
        grid.attach(Gtk.Label(label='Max emails per run:', xalign=1), 0, 5, 1, 1)
        self._max_spin = Gtk.SpinButton.new_with_range(5, 50, 5)
        self._max_spin.set_value(self.config.max_emails)
        grid.attach(self._max_spin, 1, 5, 1, 1)

        content.pack_start(grid, False, False, 0)

        # Buttons row
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        save_btn = Gtk.Button(label='Save Settings')
        save_btn.get_style_context().add_class('action-btn')
        save_btn.connect('clicked', self._on_save)
        btn_row.pack_start(save_btn, False, False, 0)

        test_btn = Gtk.Button(label='Test Telegram')
        test_btn.connect('clicked', self._on_test_telegram)
        btn_row.pack_start(test_btn, False, False, 0)

        gmail_btn = Gtk.Button(label='Connect Gmail')
        gmail_btn.connect('clicked', self._on_connect_gmail)
        btn_row.pack_start(gmail_btn, False, False, 0)

        log_btn = Gtk.Button(label='View Log')
        log_btn.connect('clicked', self._on_view_log)
        btn_row.pack_end(log_btn, False, False, 0)

        content.pack_start(btn_row, False, False, 0)

        # Gmail credentials notice
        creds_ok = os.path.exists(CREDENTIALS_FILE)
        creds_label = Gtk.Label(xalign=0)
        if creds_ok:
            creds_label.set_markup('<span color="#2e7d32">✓ Gmail credentials found</span>')
        else:
            creds_label.set_markup(
                '<span color="#c62828">✗ Gmail credentials not found — click Connect Gmail for setup instructions</span>'
            )
        creds_label.set_line_wrap(True)
        creds_label.get_style_context().add_class('meta-label')
        content.pack_start(creds_label, False, False, 0)
        self._creds_label = creds_label

        # Status bar
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._status_bar.get_style_context().add_class('status-bar')
        self._bar_label = Gtk.Label(label='', xalign=0)
        self._status_bar.pack_start(self._bar_label, True, True, 0)
        main.pack_start(self._status_bar, False, False, 0)

    def _refresh_status(self):
        last_run = self.config.get('last_run', '')
        last_status = self.config.get('last_status', '')

        if last_status.startswith('OK'):
            self._status_label.set_text(last_status)
            self._status_label.get_style_context().add_class('status-ok')
            self._status_label.get_style_context().remove_class('status-error')
        elif last_status.startswith('Error'):
            self._status_label.set_text(last_status)
            self._status_label.get_style_context().add_class('status-error')
            self._status_label.get_style_context().remove_class('status-ok')
        else:
            self._status_label.set_text('Not yet run')

        self._last_run_label.set_text(f'Last run: {last_run}' if last_run else 'Last run: never')

        interval = self.config.interval_hours
        self._next_run_label.set_text(
            f'Schedule: every {interval} hours via systemd timer'
        )

    def _on_save(self, btn):
        self.config.api_key = self._api_key_entry.get_text().strip()
        self.config.model = self._model_combo.get_active_id()
        self.config.set('telegram_token', self._tg_token_entry.get_text().strip())
        self.config.set('telegram_chat_id', self._tg_chat_entry.get_text().strip())
        self.config.set('interval_hours', int(self._interval_spin.get_value()))
        self.config.set('max_emails', int(self._max_spin.get_value()))
        self.config.save()
        self._set_bar('Settings saved.')

    def _on_test_telegram(self, btn):
        token = self._tg_token_entry.get_text().strip()
        chat_id = self._tg_chat_entry.get_text().strip()
        if not token or not chat_id:
            self._show_error('Missing details', 'Enter your Telegram token and chat ID first.')
            return
        try:
            test_connection(token, chat_id)
            self._set_bar('Test message sent to Telegram successfully.')
        except TelegramError as e:
            self._show_error('Telegram test failed', str(e))

    def _on_connect_gmail(self, btn):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text='Gmail Setup Instructions',
        )
        dialog.format_secondary_text(
            "1. Go to console.cloud.google.com\n"
            "2. Create a new project (or select an existing one)\n"
            "3. Enable the Gmail API (APIs & Services → Enable APIs)\n"
            "4. Go to APIs & Services → Credentials\n"
            "5. Create OAuth 2.0 credentials → Desktop app\n"
            "6. Download the JSON file\n"
            f"7. Save it as:\n   {CREDENTIALS_FILE}\n\n"
            "Then click 'Run Now' — a browser window will open to\n"
            "authorise Postfeed to read your Gmail."
        )
        dialog.run()
        dialog.destroy()

        # Refresh credentials label
        creds_ok = os.path.exists(CREDENTIALS_FILE)
        if creds_ok:
            self._creds_label.set_markup('<span color="#2e7d32">✓ Gmail credentials found</span>')
        else:
            self._creds_label.set_markup(
                '<span color="#c62828">✗ Gmail credentials not found</span>'
            )

    def _on_run_now(self, btn):
        if self._busy:
            return
        self._busy = True
        self._run_btn.set_sensitive(False)
        self._spinner.start()
        self._run_label.set_text('Running…')

        def run():
            import sys
            import subprocess
            try:
                result = subprocess.run(
                    [sys.executable, '/opt/postfeed/runner.py'],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    GLib.idle_add(self._on_run_done, True, 'Run complete.')
                else:
                    GLib.idle_add(self._on_run_done, False, result.stderr.strip() or 'Unknown error')
            except Exception as e:
                GLib.idle_add(self._on_run_done, False, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_run_done(self, success, msg):
        self._busy = False
        self._spinner.stop()
        self._run_btn.set_sensitive(True)
        self._run_label.set_text('')
        self.config = Config()  # reload
        self._refresh_status()
        self._set_bar(msg)

    def _on_view_log(self, btn):
        if os.path.exists(LOG_FILE):
            subprocess.Popen(['xdg-open', LOG_FILE])
        else:
            self._set_bar('No log file yet.')

    def _set_bar(self, msg):
        self._bar_label.set_text(msg)

    def _show_error(self, title, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(msg)
        dialog.run()
        dialog.destroy()
