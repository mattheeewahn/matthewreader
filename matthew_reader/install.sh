#!/bin/bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo"; exit 1; fi

APPUSER=matthew
APPDIR=/opt/matthew-reader

apt update
apt install -y cage qt6-wayland \
  python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets \
  python3-pymupdf fonts-dejavu-core libinput-tools

if ! id "$APPUSER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$APPUSER"
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR"
cp -r matthew_reader run.py "$APPDIR/"
chown -R "$APPUSER:$APPUSER" "$APPDIR"

install -m 0644 system/matthew-reader.service /etc/systemd/system/matthew-reader.service
usermod -aG video,input,render "$APPUSER"

systemctl disable getty@tty1.service 2>/dev/null || true
systemctl mask getty@tty1.service
systemctl set-default graphical.target

# Suppress normal Raspberry Pi/Linux boot branding and most console chatter.
CONFIG=/boot/firmware/config.txt
CMDLINE=/boot/firmware/cmdline.txt
if [[ -f "$CONFIG" ]] && ! grep -q '^disable_splash=1$' "$CONFIG"; then
  printf '\n# Matthew Reader kiosk\n' >> "$CONFIG"
  echo 'disable_splash=1' >> "$CONFIG"
fi
if [[ -f "$CMDLINE" ]]; then
  for arg in quiet loglevel=3 vt.global_cursor_default=0 logo.nologo; do
    grep -qw "$arg" "$CMDLINE" || sed -i "1 s/$/ $arg/" "$CMDLINE"
  done
fi

systemctl daemon-reload
systemctl enable matthew-reader.service

echo
echo "Matthew Reader installed."
echo "Reboot with: sudo reboot"
