#!/bin/bash
set -euo pipefail

CONFIG=/boot/firmware/config.txt
CMDLINE=/boot/firmware/cmdline.txt

V1=vc4-kms-dsi-7inch
V2=vc4-kms-dsi-ili9881-7inch

[[ -f "$CONFIG" ]] || {
    echo "Matthew: $CONFIG not found."
    exit 1
}

BACKUP="${CONFIG}.pre-matthew-v5_3-v1-90"
[[ -f "$BACKUP" ]] || cp -a "$CONFIG" "$BACKUP"

# Preserve dsi0 only if an old V1 line explicitly used it.
OLD_V1="$(grep -E "^[[:space:]]*dtoverlay=${V1}([,[:space:]]|$)" "$CONFIG" | head -n1 || true)"
BUS=""
if [[ "$OLD_V1" == *",dsi0"* ]]; then
    BUS=",dsi0"
fi

TMP="$(mktemp)"

# Remove old V1/V2 panel overlays and old Matthew display-detection lines.
awk -v v1="$V1" -v v2="$V2" '
{
    line=$0
    t=line
    sub(/^[[:space:]]*/, "", t)

    if (t ~ /^# Matthew Reader .*Touch Display/) next
    if (t ~ /^# Matthew Reader v5\./) next
    if (t ~ /^# Kernel rotates the panel/) next
    if (t ~ /^# Display output is rotated/) next
    if (t ~ /^# portrait \(x,y\)/) next

    p1="dtoverlay=" v1
    if (index(t,p1)==1) {
        c=substr(t,length(p1)+1,1)
        if (c=="" || c==",") next
    }

    p2="dtoverlay=" v2
    if (index(t,p2)==1) {
        c=substr(t,length(p2)+1,1)
        if (c=="" || c==",") next
    }

    # We use an explicit V1 overlay; do not auto-add another display overlay.
    if (t ~ /^display_auto_detect=/) next

    print line
}' "$CONFIG" > "$TMP"

cat >>"$TMP" <<EOF

# Matthew Reader v5.3 - official Raspberry Pi 7-inch Touch Display V1
# Native touch: 800x480
# 90 degree clockwise mapping:
#   x' = y
#   y' = 1 - x
dtoverlay=${V1}${BUS},swapxy,invy
EOF

cat "$TMP" > "$CONFIG"
rm -f "$TMP"

# Remove old DSI rotate= experiments from the kernel command line.
# The Cage/Wayland application itself is rotated by wlr-randr.
if [[ -f "$CMDLINE" ]]; then
    CB="${CMDLINE}.pre-matthew-v5_3-v1-90"
    [[ -f "$CB" ]] || cp -a "$CMDLINE" "$CB"

    python3 - "$CMDLINE" <<'PY'
import sys
p=sys.argv[1]
s=open(p,encoding="utf-8").read().strip()
tokens=s.split()
tokens=[
    t for t in tokens
    if not (t.startswith("video=DSI-") and "rotate=" in t)
]
open(p,"w",encoding="utf-8").write(" ".join(tokens)+"\n")
PY
fi

echo "Matthew v5.3 V1 90-degree configuration installed:"
echo "  panel: 800x480 Touch Display V1"
echo "  visual: 90 degrees clockwise via wlr-randr"
echo "  touch: swapxy + invy"
echo "Reboot is required."
