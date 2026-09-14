# Matthew Reader v5.3

This build keeps the complete Matthew Reader v1 → v5.2 application feature
set. The only substantive change is how the official Raspberry Pi
7-inch Touch Display 2 is rotated.

## What v5.2 got wrong

v5.2 used two independent transforms:
- Wayland/wlr-randr rotated the picture.
- Device Tree `swapxy,invx` separately rotated touch.

That can leave the picture and touch in different coordinate systems.

## v5.3 fix

On modern Raspberry Pi kernels, the official Touch Display 2 overlay supports
a `rotation` parameter. v5.3 uses only:

```text
dtoverlay=vc4-kms-dsi-ili9881-7inch,rotation=90
```

and removes:
- the Matthew `wlr-randr --transform 90` runtime rotation,
- old Matthew `swapxy/invx/invy` touch transforms,
- any `video=DSI-1:...,rotate=...` argument added during troubleshooting.

That gives one source of truth for both display and touch.

## Install

```bash
cd ~/matthewreader/MatthewReader_v5_3
sudo bash install.sh
sudo reboot
```

A reboot is mandatory.

## Diagnose after reboot

```bash
sudo matthew-touch-diagnostics
```

Live raw touch events:

```bash
sudo libinput debug-events
```
