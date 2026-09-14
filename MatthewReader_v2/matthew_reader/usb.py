from __future__ import annotations
from pathlib import Path
import os, shutil

SUPPORTED = {".pdf", ".matthew", ".matthewscr"}

def usb_mounts():
    """Return currently mounted removable-media directories used by udiskie/UDisks."""
    roots = [
        Path("/run/media") / os.environ.get("USER", "matthew"),
        Path("/media") / os.environ.get("USER", "matthew"),
        Path("/media"),
    ]
    seen, result = set(), []
    for root in roots:
        if not root.exists():
            continue
        try:
            children = list(root.iterdir())
        except PermissionError:
            continue
        for p in children:
            try:
                rp = p.resolve()
                # /media may contain /media/$USER, don't report the container folder itself.
                if p.name == os.environ.get("USER", "matthew") and root == Path("/media"):
                    continue
                if p.is_dir() and str(rp) not in seen:
                    seen.add(str(rp))
                    result.append(p)
            except OSError:
                pass
    return result

def scan_importable(limit=500):
    found = []
    for mount in usb_mounts():
        for base, dirs, files in os.walk(mount):
            # Avoid traversing hidden/system directories where possible.
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"System Volume Information"}]
            for name in files:
                p = Path(base) / name
                if p.suffix.lower() in SUPPORTED:
                    found.append(p)
                    if len(found) >= limit:
                        return found
    return found

def unique_destination(folder: Path, name: str):
    dest = folder / name
    if not dest.exists():
        return dest
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 1
    while True:
        candidate = folder / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def copy_into_library(src: Path, books_dir: Path, notes_dir: Path):
    src = Path(src)
    if src.suffix.lower() == ".pdf":
        dest = unique_destination(books_dir, src.name)
        shutil.copy2(src, dest)
        sidecar = src.with_suffix(".matthewanno")
        if sidecar.exists():
            shutil.copy2(sidecar, dest.with_suffix(".matthewanno"))
        return dest
    if src.suffix.lower() in {".matthew", ".matthewscr"}:
        dest = unique_destination(notes_dir, src.name)
        shutil.copy2(src, dest)
        return dest
    raise ValueError("Unsupported file type")
