from __future__ import annotations
import json,os,shutil,subprocess,socket
from pathlib import Path

SETTINGS_FILE=Path.home()/"MatthewReader"/"settings.json"
DEFAULTS={"screen_timeout":10,"brightness":70}

def load_settings():
    try:
        d=json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        d={}
    out=DEFAULTS.copy();out.update(d);return out

def save_settings(d):
    SETTINGS_FILE.parent.mkdir(parents=True,exist_ok=True)
    tmp=SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d,indent=2),encoding="utf-8")
    tmp.replace(SETTINGS_FILE)

def run(cmd,timeout=20):
    try:
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
        return p.returncode,p.stdout.strip(),p.stderr.strip()
    except Exception as e:
        return 1,"",str(e)

def current_wifi():
    rc,out,err=run(["nmcli","-t","-f","ACTIVE,SSID","dev","wifi"])
    if rc: return ""
    for line in out.splitlines():
        if line.startswith("yes:"):return line[4:]
    return ""

def wifi_networks():
    run(["nmcli","radio","wifi","on"])
    rc,out,err=run(["nmcli","-t","--escape","no","-f","SSID,SIGNAL,SECURITY","dev","wifi","list","--rescan","yes"],30)
    result=[];seen=set()
    if rc:return result
    for line in out.splitlines():
        parts=line.split(":",2)
        if len(parts)<3:continue
        ssid,signal,security=parts
        if not ssid or ssid in seen:continue
        seen.add(ssid)
        result.append((ssid,signal,security))
    result.sort(key=lambda x:int(x[1]) if x[1].isdigit() else 0,reverse=True)
    return result

def connect_wifi(ssid,password=""):
    cmd=["nmcli","dev","wifi","connect",ssid]
    if password:cmd+=["password",password]
    return run(cmd,40)

def set_brightness(percent):
    return run(["sudo","-n","/usr/local/bin/matthew-brightness",str(int(percent))])

def device_info():
    total,used,free=shutil.disk_usage(Path.home())
    rc,ip,_=run(["hostname","-I"])
    return {
        "hostname":socket.gethostname(),
        "ip":ip.split()[0] if ip else "Not connected",
        "storage_total":round(total/1024**3,1),
        "storage_free":round(free/1024**3,1),
    }

def power_action(action):
    if action not in {"reboot","poweroff"}:return (1,"","Invalid action")
    return run(["sudo","-n","/usr/local/bin/matthew-power",action])
