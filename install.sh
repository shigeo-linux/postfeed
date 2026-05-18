#!/bin/bash
set -e

APP_NAME="postfeed"
INSTALL_DIR="/opt/${APP_NAME}"
DESKTOP_DIR="/usr/share/applications"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=== Installing ${APP_NAME} ==="

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    exit 1
fi

echo "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-requests

sudo pip3 install --break-system-packages \
    google-auth-oauthlib google-auth-httplib2 google-api-python-client

echo "Copying application files..."
sudo mkdir -p "${INSTALL_DIR}"
sudo cp -r "$(dirname "$0")"/* "${INSTALL_DIR}/"
sudo chmod +x "${INSTALL_DIR}/postfeed.py"
sudo chmod +x "${INSTALL_DIR}/runner.py"

echo "Installing icon..."
sudo mkdir -p /usr/share/icons/hicolor/scalable/apps
sudo cp "${INSTALL_DIR}/postfeed.svg" /usr/share/icons/hicolor/scalable/apps/postfeed.svg
sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

echo "Installing desktop entry..."
sudo cp "${INSTALL_DIR}/postfeed.desktop" "${DESKTOP_DIR}/"
sudo update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

echo "Creating launcher..."
sudo tee /usr/local/bin/postfeed > /dev/null << 'EOF'
#!/bin/bash
exec python3 /opt/postfeed/postfeed.py "$@"
EOF
sudo chmod +x /usr/local/bin/postfeed

echo "Creating config directory..."
mkdir -p "$HOME/.config/${APP_NAME}"

echo "Installing systemd user timer..."
mkdir -p "${SYSTEMD_USER_DIR}"
cp "${INSTALL_DIR}/postfeed.service" "${SYSTEMD_USER_DIR}/postfeed.service"
cp "${INSTALL_DIR}/postfeed.timer" "${SYSTEMD_USER_DIR}/postfeed.timer"

# Update service to run as current user
sed -i "s|User=%i|User=$(whoami)|" "${SYSTEMD_USER_DIR}/postfeed.service"

sudo loginctl enable-linger "$(whoami)"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
if systemctl --user daemon-reload 2>/dev/null; then
    systemctl --user enable postfeed.timer
    systemctl --user start postfeed.timer
else
    echo "Note: Timer files installed. Run 'systemctl --user enable --now postfeed.timer' after logging in."
fi

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Run: postfeed"
echo "Or search for 'Postfeed' in your application menu."
echo ""
echo "Next steps:"
echo "  1. Open Postfeed and enter your OpenRouter API key"
echo "  2. Enter your Telegram bot token and chat ID"
echo "  3. Set up Gmail credentials (click 'Connect Gmail' for instructions)"
echo "  4. Click 'Run Now' to test"
echo ""
echo "The timer will run automatically every 12 hours."
