#!/usr/bin/env bash
# Install FDA pipeline systemd user units
# Run from the project directory: bash systemd/install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="${HOME}/.config/systemd/user"

echo "Installing FDA pipeline systemd user units..."

# Create systemd user directory if it doesn't exist
mkdir -p "$SYSTEMD_DIR"

# Copy unit files
cp "${SCRIPT_DIR}/fda-pipeline.service" "$SYSTEMD_DIR/"
cp "${SCRIPT_DIR}/fda-pipeline.timer" "$SYSTEMD_DIR/"

# Reload systemd daemon
systemctl --user daemon-reload

# Enable and start the timer
systemctl --user enable fda-pipeline.timer
systemctl --user start fda-pipeline.timer

echo ""
echo "✓ FDA pipeline timer installed and enabled"
echo ""
echo "Useful commands:"
echo "  systemctl --user status fda-pipeline.timer   # Check timer status"
echo "  systemctl --user list-timers                  # List all user timers"
echo "  journalctl --user -u fda-pipeline.service     # View pipeline logs"
echo "  systemctl --user start fda-pipeline.service   # Run pipeline manually"
echo "  systemctl --user stop fda-pipeline.timer      # Disable timer"
echo ""
echo "Pushover notifications require ~/.config/fda-pipeline/.env with:"
echo "  PUSHOVER_APP_KEY=your_app_key"
echo "  PUSHOVER_USER_KEY=your_user_key"