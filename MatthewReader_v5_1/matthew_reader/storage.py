from __future__ import annotations
import json, zipfile
from pathlib import Path
from datetime import datetime

APP_DIR = Path.home() / "MatthewReader"
LIBRARY_DIR = APP_DIR / "library"
NOTES_DIR = LIBRARY_DIR / "notes"
BOOKS_DIR = LIBRARY_DIR / "books"
EXPORT_DIR = APP_DIR / "exports"
COVERS_DIR = APP_DIR / "covers"
STATE_FILE = APP_DIR / "state.json"
META_FILE = APP_DIR / "library_meta.json"

def ensure_dirs():
    for p in (APP_DIR, LIBRARY_DIR, NOTES_DIR, BOOKS_DIR, EXPORT_DIR, COVERS_DIR):
        p.mkdir(parents=True, exist_ok=True)
    for p in (STATE_FILE, META_FILE):
        if not p.exists(): p.write_text("{}", encoding="utf-8")

def now_iso(): return datetime.now().isoformat(timespec="seconds")

def save_note(path: Path, title: str, pages, kind="matthew", template="blank"):
    path=Path(path); created=now_iso()
    if path.exists():
        try: created=load_note(path)[0].get("created",created)
        except Exception: pass
    manifest={"format":"MatthewNote","version":5,"kind":kind,"title":title,"template":template,
              "created":created,"modified":now_iso(),"page_count":len(pages)}
    tmp=path.with_suffix(path.suffix+".tmp")
    with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json",json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr("pages.json",json.dumps(pages,ensure_ascii=False))
    tmp.replace(path)

def load_note(path: Path):
    with zipfile.ZipFile(path,"r") as z:
        manifest=json.loads(z.read("manifest.json")); pages=json.loads(z.read("pages.json"))
    migrated=[]
    for page in pages:
        objs=[]
        for obj in page:
            if isinstance(obj,dict) and "type" not in obj:
                obj=dict(obj); obj["type"]="stroke"
            objs.append(obj)
        migrated.append(objs)
    return manifest,migrated

def annotation_path(pdf_path: Path): return Path(pdf_path).with_suffix(".matthewanno")

def load_annotations(pdf_path: Path):
    p=annotation_path(pdf_path)
    base={"format":"MatthewAnnotation","version":5,"pdf":Path(pdf_path).name,"pages":{},"bookmarks":[]}
    if not p.exists(): return base
    try:
        d=json.loads(p.read_text(encoding="utf-8")); d.setdefault("pages",{}); d.setdefault("bookmarks",[]); return d
    except Exception: return base

def save_annotations(pdf_path: Path,data):
    p=annotation_path(pdf_path); tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(p)

def _load_json(path):
    ensure_dirs()
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {}

def _save_json(path,data):
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(path)

def load_state(): return _load_json(STATE_FILE)
def document_state(path: Path): return load_state().get(str(Path(path).resolve()),{})
def update_document_state(path: Path,**values):
    s=load_state(); key=str(Path(path).resolve()); s.setdefault(key,{}).update(values); _save_json(STATE_FILE,s)

def load_meta(): return _load_json(META_FILE)
def doc_meta(path: Path): return load_meta().get(str(Path(path).resolve()),{})
def update_doc_meta(path: Path,**values):
    m=load_meta(); key=str(Path(path).resolve()); m.setdefault(key,{}).update(values); _save_json(META_FILE,m)

def mark_opened(path: Path): update_doc_meta(path,last_opened=now_iso())
def toggle_favorite(path: Path):
    cur=bool(doc_meta(path).get("favorite",False)); update_doc_meta(path,favorite=not cur); return not cur

def set_subject(path: Path,subject: str): update_doc_meta(path,subject=subject.strip())
def subjects():
    return sorted({v.get("subject","").strip() for v in load_meta().values() if v.get("subject","").strip()}, key=str.lower)

def _all_items():
    ensure_dirs(); items=[]
    for p in sorted(BOOKS_DIR.glob("*.pdf")):
        md=doc_meta(p); items.append({"type":"pdf","path":p,"title":p.stem,**md})
    for ext,typ in (("*.matthew","note"),("*.matthewscr","scratch")):
        for p in sorted(NOTES_DIR.glob(ext)):
            try: title=load_note(p)[0].get("title",p.stem)
            except Exception: title=p.stem
            md=doc_meta(p); items.append({"type":typ,"path":p,"title":title,**md})
    return items

def list_library(query="",category="all",subject=""):
    q=query.strip().lower(); items=_all_items()
    if q: items=[x for x in items if q in x["title"].lower()]
    if category=="favorites": items=[x for x in items if x.get("favorite",False)]
    elif category=="recent":
        items=[x for x in items if x.get("last_opened")]
        items.sort(key=lambda x:x.get("last_opened",""),reverse=True)
        return items[:30]
    elif category=="textbooks": items=[x for x in items if x["type"]=="pdf"]
    elif category=="notes": items=[x for x in items if x["type"]=="note"]
    elif category=="scratch": items=[x for x in items if x["type"]=="scratch"]
    if subject: items=[x for x in items if x.get("subject","")==subject]
    items.sort(key=lambda x:x["title"].lower())
    return items
