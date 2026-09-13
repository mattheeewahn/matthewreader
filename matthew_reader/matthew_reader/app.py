from __future__ import annotations
from pathlib import Path
import shutil
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QStackedWidget,QScrollArea,QGridLayout,QInputDialog,QFileDialog,QMessageBox,QFrame)
from PySide6.QtCore import Qt
from .storage import ensure_dirs, list_library, NOTES_DIR, BOOKS_DIR, save_note, load_note
from .canvas import InkCanvas
from .pdfviewer import PDFViewer

STYLE = """
* { font-family: 'DejaVu Sans'; font-size: 16px; color:#202020; }
QMainWindow,QWidget { background:#f6f4ee; }
QPushButton { background:#f6f4ee; border:1px solid #b9b5aa; border-radius:5px; padding:10px 14px; }
QPushButton:pressed { background:#ddd9cf; }
QPushButton#primary { background:#202020; color:white; border:none; }
QLabel#title { font-size:30px; font-weight:600; }
QFrame#card { background:#fbfaf6; border:1px solid #d2cec4; border-radius:6px; }
"""

class ReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.setWindowTitle("Matthew")
        self.setStyleSheet(STYLE)
        self.showFullScreen()
        self.stack=QStackedWidget(); self.setCentralWidget(self.stack)
        self.library=LibraryPage(self)
        self.stack.addWidget(self.library)

    def go_library(self):
        self.library.refresh(); self.stack.setCurrentWidget(self.library)

    def open_note(self,path):
        w=NotePage(self,path)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)

    def open_pdf(self,path):
        w=PDFPage(self,path)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)

class LibraryPage(QWidget):
    def __init__(self,app):
        super().__init__(); self.app=app
        self.v=QVBoxLayout(self); self.v.setContentsMargins(26,20,26,20); self.v.setSpacing(14)
        top=QHBoxLayout()
        t=QLabel("Library"); t.setObjectName("title"); top.addWidget(t); top.addStretch()
        b=QPushButton("+ New Note"); b.setObjectName("primary"); b.clicked.connect(self.new_note); top.addWidget(b)
        s=QPushButton("+ Scratch"); s.clicked.connect(self.new_scratch); top.addWidget(s)
        imp=QPushButton("Import PDF"); imp.clicked.connect(self.import_pdf); top.addWidget(imp)
        self.v.addLayout(top)
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.v.addWidget(self.scroll); self.refresh()

    def refresh(self):
        host=QWidget(); g=QGridLayout(host); g.setSpacing(16)
        items=list_library()
        if not items:
            empty=QLabel("No books or notes yet.\nCreate a note or import a PDF.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter); g.addWidget(empty,0,0)
        for i,item in enumerate(items):
            card=QPushButton(f"{item['title']}\n\n{item['type'].upper()}")
            card.setMinimumSize(190,145); card.setMaximumWidth(240)
            if item["type"]=="pdf":
                card.clicked.connect(lambda _,p=item["path"]: self.app.open_pdf(p))
            else:
                card.clicked.connect(lambda _,p=item["path"]: self.app.open_note(p))
            g.addWidget(card,i//3,i%3)
        g.setRowStretch((len(items)+2)//3,1); self.scroll.setWidget(host)

    def _create(self,ext,kind):
        title,ok=QInputDialog.getText(self,"New Note","Title:")
        if not ok or not title.strip(): return
        safe="".join(c for c in title if c not in r'\/:*?"<>|').strip() or "Untitled"
        p=NOTES_DIR/f"{safe}{ext}"
        n=1
        while p.exists(): p=NOTES_DIR/f"{safe} {n}{ext}"; n+=1
        save_note(p,title.strip(),[[]],kind)
        self.refresh(); self.app.open_note(p)
    def new_note(self): self._create(".matthew","matthew")
    def new_scratch(self): self._create(".matthewscr","scratch")

    def import_pdf(self):
        src,_=QFileDialog.getOpenFileName(self,"Import PDF","/media","PDF Files (*.pdf)")
        if not src: return
        dst=BOOKS_DIR/Path(src).name
        if dst.exists():
            QMessageBox.warning(self,"Already exists","A PDF with that name already exists."); return
        shutil.copy2(src,dst); self.refresh()

class NotePage(QWidget):
    def __init__(self,app,path):
        super().__init__(); self.app=app; self.path=Path(path)
        self.manifest,self.pages=load_note(self.path); self.page=0
        v=QVBoxLayout(self); v.setContentsMargins(14,10,14,12); v.setSpacing(8)
        top=QHBoxLayout()
        back=QPushButton("‹ Library"); back.clicked.connect(self.save_and_back); top.addWidget(back)
        self.title=QLabel(self.manifest.get("title",self.path.stem)); top.addWidget(self.title); top.addStretch()
        self.page_lbl=QLabel(); top.addWidget(self.page_lbl)
        v.addLayout(top)
        self.canvas=InkCanvas(); self.canvas.set_page(self.pages[0]); self.canvas.changed.connect(self.autosave); v.addWidget(self.canvas,1)
        bar=QHBoxLayout()
        for label,tool in [("Pen","pen"),("Eraser","eraser")]:
            b=QPushButton(label); b.clicked.connect(lambda _,t=tool:self.canvas.set_tool(t)); bar.addWidget(b)
        undo=QPushButton("Undo"); undo.clicked.connect(self.canvas.undo); bar.addWidget(undo)
        prev=QPushButton("‹"); prev.clicked.connect(self.prev_page); bar.addWidget(prev)
        nxt=QPushButton("›"); nxt.clicked.connect(self.next_page); bar.addWidget(nxt)
        add=QPushButton("+ Page"); add.clicked.connect(self.add_page); bar.addWidget(add)
        v.addLayout(bar); self.update_label()

    def autosave(self):
        self.pages[self.page]=self.canvas.strokes
        save_note(self.path,self.manifest.get("title",self.path.stem),self.pages,self.manifest.get("kind","matthew"))
    def save_and_back(self): self.autosave(); self.app.go_library()
    def update_label(self): self.page_lbl.setText(f"{self.page+1} / {len(self.pages)}")
    def show_page(self): self.canvas.set_page(self.pages[self.page]); self.update_label()
    def prev_page(self):
        self.autosave()
        if self.page>0: self.page-=1; self.show_page()
    def next_page(self):
        self.autosave()
        if self.page<len(self.pages)-1: self.page+=1; self.show_page()
    def add_page(self):
        self.autosave(); self.pages.append([]); self.page=len(self.pages)-1; self.show_page(); self.autosave()

class PDFPage(QWidget):
    def __init__(self,app,path):
        super().__init__(); self.app=app; self.path=Path(path)
        v=QVBoxLayout(self); v.setContentsMargins(8,8,8,8); v.setSpacing(6)
        top=QHBoxLayout()
        back=QPushButton("‹ Library"); back.clicked.connect(app.go_library); top.addWidget(back)
        top.addWidget(QLabel(self.path.stem)); top.addStretch()
        self.pg=QLabel(); top.addWidget(self.pg); v.addLayout(top)
        self.viewer=PDFViewer(self.path); self.viewer.pageChanged.connect(lambda a,b:self.pg.setText(f"{a} / {b}")); v.addWidget(self.viewer,1)
        bar=QHBoxLayout()
        read=QPushButton("Read"); read.clicked.connect(lambda:self.viewer.set_mode("read")); bar.addWidget(read)
        pen=QPushButton("Pen"); pen.clicked.connect(lambda:self.viewer.set_pen("#222222")); bar.addWidget(pen)
        for name,c in [("Y","yellow"),("G","green"),("B","blue"),("P","pink")]:
            b=QPushButton(name); b.clicked.connect(lambda _,x=c:self.viewer.set_highlight(x)); bar.addWidget(b)
        undo=QPushButton("Undo"); undo.clicked.connect(self.viewer.undo); bar.addWidget(undo)
        prev=QPushButton("‹"); prev.clicked.connect(self.viewer.prev_page); bar.addWidget(prev)
        nxt=QPushButton("›"); nxt.clicked.connect(self.viewer.next_page); bar.addWidget(nxt)
        v.addLayout(bar)
