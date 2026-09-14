from pathlib import Path
import os, shutil

SUPPORTED={".pdf",".matthew",".matthewscr"}

def usb_mounts():
    user=os.environ.get("USER","matthew")
    roots=[Path("/run/media")/user,Path("/media")/user,Path("/media")]
    seen=[]; out=[]
    for root in roots:
        if not root.exists(): continue
        try: kids=list(root.iterdir())
        except Exception: continue
        for p in kids:
            if root==Path("/media") and p.name==user: continue
            try:
                rp=str(p.resolve())
                if p.is_dir() and rp not in seen:
                    seen.append(rp); out.append(p)
            except Exception: pass
    return out

def scan_importable(limit=500):
    out=[]
    for mount in usb_mounts():
        for base,dirs,files in os.walk(mount):
            dirs[:]=[d for d in dirs if not d.startswith(".") and d!="System Volume Information"]
            for name in files:
                p=Path(base)/name
                if p.suffix.lower() in SUPPORTED:
                    out.append(p)
                    if len(out)>=limit:return out
    return out

def _unique(folder,name):
    p=folder/name
    if not p.exists():return p
    stem,suf=Path(name).stem,Path(name).suffix;i=1
    while True:
        c=folder/f"{stem} ({i}){suf}"
        if not c.exists():return c
        i+=1

def copy_into_library(src,books_dir,notes_dir):
    src=Path(src)
    folder=books_dir if src.suffix.lower()==".pdf" else notes_dir
    dest=_unique(folder,src.name);shutil.copy2(src,dest)
    if src.suffix.lower()==".pdf":
        anno=src.with_suffix(".matthewanno")
        if anno.exists():shutil.copy2(anno,dest.with_suffix(".matthewanno"))
    return dest
