#!/usr/bin/env bash
#
# Install drone_alarm as a systemd system service running as the `nobody` user.
#
# Run as root from a checkout of the repo:
#   sudo ./install.sh
#
# It is safe to re-run: the first run lays down the files and stops so you can fill in
# config.yaml; the second run logs in to Telegram and starts the service.

set -euo pipefail

APP_DIR=/opt/drone_alarm
STATE_DIR=/var/lib/drone_alarm
SERVICE_USER=nobody
UNIT=drone_alarm.service
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use: sudo ./install.sh)." >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3 (and python3-venv) first." >&2
    exit 1
fi

# `nobody`'s primary group is `nogroup` on Debian/Ubuntu, `nobody` elsewhere.
if getent group nogroup >/dev/null 2>&1; then
    SERVICE_GROUP=nogroup
else
    SERVICE_GROUP=nobody
fi
echo "Service account: ${SERVICE_USER}:${SERVICE_GROUP}"

# 1. Copy the application into /opt (never clobber an existing config.yaml).
#    Skip when already running from the install target (e.g. /opt/drone_alarm).
if [[ "$(realpath "$SRC_DIR")" == "$(realpath -m "$APP_DIR")" ]]; then
    echo "==> Running from ${APP_DIR}; skipping application copy"
else
    echo "==> Installing application to ${APP_DIR}"
    mkdir -p "$APP_DIR"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete \
            --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
            --exclude 'config.yaml' --exclude '*.session' \
            "$SRC_DIR"/ "$APP_DIR"/
    else
        cp -a "$SRC_DIR"/. "$APP_DIR"/
        rm -rf "$APP_DIR/.git" "$APP_DIR/.venv" "$APP_DIR/__pycache__"
    fi
fi

# 2. Create the virtualenv and install dependencies.
echo "==> Creating virtualenv and installing dependencies"
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# 3. Ensure config.yaml exists and is filled in. Stop here on first run so the operator
#    can edit it before we attempt a Telegram login.
if [[ ! -f "$APP_DIR/config.yaml" ]]; then
    cp "$APP_DIR/config.example.yaml" "$APP_DIR/config.yaml"
    echo "Created ${APP_DIR}/config.yaml from the template."
fi
chown root:"$SERVICE_GROUP" "$APP_DIR/config.yaml"
chmod 640 "$APP_DIR/config.yaml"
if grep -q 'your_api_hash_here' "$APP_DIR/config.yaml"; then
    echo
    echo "==> Edit ${APP_DIR}/config.yaml (api_id/api_hash/phone, channels, keywords),"
    echo "    then re-run: sudo ${APP_DIR}/install.sh"
    exit 0
fi

# 4. Prepare the writable state directory for the .session (an account credential).
echo "==> Preparing state directory ${STATE_DIR}"
mkdir -p "$STATE_DIR"
chown "$SERVICE_USER":"$SERVICE_GROUP" "$STATE_DIR"
chmod 700 "$STATE_DIR"

# 5. One-time interactive Telegram login (creates the .session) if not already present.
if ! ls "$STATE_DIR"/*.session >/dev/null 2>&1; then
    echo "==> Logging in to Telegram (enter the code Telegram sends you)"
    ( cd "$STATE_DIR" && sudo -u "$SERVICE_USER" \
        "$APP_DIR/.venv/bin/python" "$APP_DIR/drone_alarm.py" --login )
fi
chown "$SERVICE_USER":"$SERVICE_GROUP" "$STATE_DIR"/*.session
chmod 600 "$STATE_DIR"/*.session

# 6. Install the unit (patching Group= to this system's group) and start the service.
echo "==> Installing systemd unit and starting the service"
sed "s/^Group=.*/Group=${SERVICE_GROUP}/" "$APP_DIR/$UNIT" > "/etc/systemd/system/$UNIT"
systemctl daemon-reload
systemctl enable --now "$UNIT"

echo
echo "Done. The service is running. Follow alerts with:"
echo "    journalctl -u drone_alarm -f"
