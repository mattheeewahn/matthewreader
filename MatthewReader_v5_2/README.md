# Matthew Reader v5.2

v5.2 keeps the v1 → v5.1 feature set and fixes the official Raspberry Pi
7-inch Touch Display 2 orientation as one coordinated configuration:

- **Display:** always 90° clockwise under Cage/Wayland
- **Touch X/Y:** `swapxy`
- **Touch direction:** `invx`
- **Qt standard controls:** v5.1 touch-to-click compatibility retained
- **InkCanvas/PDFViewer:** native multi-touch retained
- **Pinch zoom / handwriting:** retained

The Touch Display 2 is natively 720×1280 portrait. After Matthew's fixed
90° clockwise transform, the UI is landscape and the touch mapping follows
the same transform.

## Install / upgrade

```bash
cd ~/matthewreader/MatthewReader_v5_2
sudo bash install.sh
sudo reboot
```

A reboot is required because the touchscreen Device Tree mapping is read at boot.

## Diagnostics

After reboot:

```bash
sudo matthew-touch-diagnostics
```

For live raw touch events:

```bash
sudo libinput debug-events
```

## Rollback of boot touch configuration

The first v5.2 install backs up the previous boot configuration to:

```text
/boot/firmware/config.txt.pre-matthew-touch
```

All previous Matthew Reader application/library formats are retained.
