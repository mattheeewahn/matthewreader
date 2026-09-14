# Matthew Reader v4

## New in v4
- Built-in full-screen touch QWERTY keyboard
- Touch keyboard works for:
  - Library search
  - New notebook names
  - PDF text search
  - Text objects
  - Wi-Fi passwords
- Settings screen
- Wi-Fi scan/connect using Raspberry Pi OS NetworkManager (`nmcli`)
- Display brightness control
- Configurable screen timeout (Never / 1 / 5 / 10 / 30 min)
- Matthew sleep screen with tap-to-wake
- Device information (hostname, IP, storage)
- Restart and Power Off buttons
- All v3 note/PDF/USB features retained

The built-in keyboard currently uses an English QWERTY layout plus numbers/symbols.
A Korean IME is not yet included.

## Upgrade
```bash
cd ~/matthewreader
git pull
sudo bash install.sh
sudo reboot
```

## Important
`install.sh` installs two narrow root helpers:
- `/usr/local/bin/matthew-brightness`
- `/usr/local/bin/matthew-power`

Only these helpers are granted passwordless sudo to the `matthew` kiosk account.
