from __future__ import annotations
import json, zipfile
from pathlib import Path
from datetime import datetime

APP_DIR = Path.home() / "MatthewReader"
LIBRARY_DIR = APP_DIR / "library"
NOTES_DIR = LIBRARY_DIR / "notes"
BOOKS_DIR = LIBRARY_DIR / "books"

def ensure_dirs():
    for p in (APP_DIR, LIBRARY_DIR, NOTES_DIR, BOOKS_DIR):
        p.mkdir(parents=True, exist_ok=True)

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def _manifest(title, pages, kind):
    return {
        "format": "MatthewNote",
        "version": 2,
        "kind": kind,
        "title": title,
        "created": now_iso(),
        "modified": now_iso(),
        "page_count": len(pages),
    }

def save_note(path: Path, title: str, pages, kind="matthew"):
    path = Path(path)
    manifest = _manifest(title, pages, kind)
    # Atomic-ish replace: write next to target, then replace.
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("pages.json", json.dumps(pages, ensure_ascii=False))
    tmp.replace(path)
    return path

def load_note(path: Path):
    with zipfile.ZipFile(path, "r") as z:
        manifest = json.loads(z.read("manifest.json"))
        pages = json.loads(z.read("pages.json"))
    return manifest, pages

def annotation_path(pdf_path: Path) -> Path:
    return Path(pdf_path).with_suffix(".matthewanno")

def load_annotations(pdf_path: Path):
    p = annotation_path(pdf_path)
    if not p.exists():
        return {"format":"MatthewAnnotation","version":2,"pdf":Path(pdf_path).name,"pages":{}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"format":"MatthewAnnotation","version":2,"pdf":Path(pdf_path).name,"pages":{}}

def save_annotations(pdf_path: Path, data):
    p = annotation_path(pdf_path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)

def list_library():
    ensure_dirs()
    items = []
    for p in sorted(BOOKS_DIR.glob("*.pdf")):
        items.append({"type":"pdf","path":p,"title":p.stem})
    for ext, typ in (("*.matthew","note"),("*.matthewscr","scratch")):
        for p in sorted(NOTES_DIR.glob(ext)):
            try:
                m,_ = load_note(p)
                title = m.get("title", p.stem)
            except Exception:
                title = p.stem
            items.append({"type":typ,"path":p,"title":title})
    return items
