# Matthew Reader v5.3 — Touch Display V1 90°

This package keeps the **Matthew Reader v5.3 application code and features**
and changes only the display/touch setup for the original official Raspberry
Pi 7-inch Touch Display.

- Hardware: Touch Display V1
- Native resolution: 800×480
- Matthew orientation: 480×800 portrait
- Visual rotation: 90° clockwise
- Touch mapping: `swapxy,invy`

## Install

```bash
cd ~/matthewreader/MatthewReader_v5_3_V1_90
sudo bash install.sh
sudo reboot
```

## Diagnose

```bash
sudo matthew-touch-diagnostics
```

Expected:

```text
800x480
dtoverlay=vc4-kms-dsi-7inch,swapxy,invy
Wayland transform: 90
```
