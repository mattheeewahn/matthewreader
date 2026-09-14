from __future__ import annotations
import json, zipfile
from pathlib import Path
from datetime import datetime

APP_DIR = Path.home() / "MatthewReader"
LIBRARY_DIR = APP_DIR / "library"
NOTES_DIR = LIBRARY_DIR / "notes"
BOOKS_DIR = LIBRARY_DIR / "books"
STATE_FILE = APP_DIR / "state.json"

def ensure_dirs():
    for p in (APP_DIR, LIBRARY_DIR, NOTES_DIR, BOOKS_DIR):
        p.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text("{}", encoding="utf-8")

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def save_note(path: Path, title: str, pages, kind="matthew", template="blank"):
    path = Path(path)
    created = now_iso()
    if path.exists():
        try:
            created = load_note(path)[0].get("created", created)
        except Exception:
            pass
    manifest = {
        "format":"MatthewNote","version":3,"kind":kind,"title":title,
        "template":template,"created":created,"modified":now_iso(),
        "page_count":len(pages),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("pages.json", json.dumps(pages, ensure_ascii=False))
    tmp.replace(path)

def load_note(path: Path):
    with zipfile.ZipFile(path, "r") as z:
        manifest = json.loads(z.read("manifest.json"))
        pages = json.loads(z.read("pages.json"))
    migrated=[]
    for page in pages:
        objs=[]
        for obj in page:
            if isinstance(obj,dict) and "type" not in obj:
                obj=dict(obj); obj["type"]="stroke"
            objs.append(obj)
        migrated.append(objs)
    return manifest,migrated

def annotation_path(pdf_path: Path):
    return Path(pdf_path).with_suffix(".matthewanno")

def load_annotations(pdf_path: Path):
    p=annotation_path(pdf_path)
    if not p.exists():
        return {"format":"MatthewAnnotation","version":3,"pdf":Path(pdf_path).name,"pages":{},"bookmarks":[]}
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
        d.setdefault("pages",{}); d.setdefault("bookmarks",[])
        return d
    except Exception:
        return {"format":"MatthewAnnotation","version":3,"pdf":Path(pdf_path).name,"pages":{},"bookmarks":[]}

def save_annotations(pdf_path: Path, data):
    p=annotation_path(pdf_path)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(p)

def load_state():
    ensure_dirs()
    try: return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception: return {}

def update_document_state(path: Path, **values):
    s=load_state(); key=str(Path(path).resolve()); s.setdefault(key,{}).update(values)
    tmp=STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(STATE_FILE)

def document_state(path: Path):
    return load_state().get(str(Path(path).resolve()),{})

def list_library(query=""):
    ensure_dirs(); q=query.strip().lower(); items=[]
    for p in sorted(BOOKS_DIR.glob("*.pdf")):
        if not q or q in p.stem.lower():
            items.append({"type":"pdf","path":p,"title":p.stem})
    for ext,typ in (("*.matthew","note"),("*.matthewscr","scratch")):
        for p in sorted(NOTES_DIR.glob(ext)):
            try: title=load_note(p)[0].get("title",p.stem)
            except Exception: title=p.stem
            if not q or q in title.lower():
                items.append({"type":typ,"path":p,"title":title})
    return items
