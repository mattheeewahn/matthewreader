from pathlib import Path
import hashlib
import pymupdf as fitz
from .storage import COVERS_DIR, ensure_dirs

def cover_path(pdf_path: Path):
    ensure_dirs(); p=Path(pdf_path); key=hashlib.sha1(str(p.resolve()).encode()).hexdigest()[:18]
    return COVERS_DIR/f"{key}.png"

def ensure_pdf_cover(pdf_path: Path):
    pdf_path=Path(pdf_path); out=cover_path(pdf_path)
    try:
        if out.exists() and out.stat().st_mtime >= pdf_path.stat().st_mtime: return out
        doc=fitz.open(str(pdf_path))
        if len(doc)<1:return None
        pg=doc.load_page(0); pix=pg.get_pixmap(matrix=fitz.Matrix(0.6,0.6),alpha=False)
        pix.save(str(out)); doc.close(); return out
    except Exception:
        return None
