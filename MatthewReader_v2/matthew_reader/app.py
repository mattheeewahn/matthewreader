from __future__ import annotations
from pathlib import Path
import shutil
from PySide6.QtWidgets import (
    QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QStackedWidget,QScrollArea,QGridLayout,QInputDialog,QFileDialog,
    QMessageBox,QFrame,QDialog,QListWidget,QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer
from .storage import ensure_dirs, list_library, NOTES_DIR, BOOKS_DIR, save_note, load_note
from .canvas import InkCanvas
from .pdfviewer import PDFViewer
from .usb import usb_mounts, scan_importable, copy_into_library

STYLE = """
* { font-family: 'DejaVu Sans'; font-size: 15px; color:#202020; }
QMainWindow,QWidget { background:#f6f4ee; }
QPushButton {
    background:#f6f4ee; border:1px solid #b9b5aa;
    border-radius:5px; padding:8px 10px; min-height:30px;
}
QPushButton:pressed { background:#ddd9cf; }
QPushButton#primary { background:#202020; color:white; border:none; }
QPushButton#toolOn { background:#d9d5ca; border:1px solid #777268; }
QLabel#title { font-size:27px; font-weight:600; }
QLabel#muted { color:#777268; font-size:13px; }
QFrame#card { background:#fbfaf6; border:1px solid #d2cec4; border-radius:6px; }
QListWidget { background:#fbfaf6; border:1px solid #c8c4ba; }
"""

class ReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.setWindowTitle("Matthew")
        self.setStyleSheet(STYLE)
        self.stack=QStackedWidget()
        self.setCentralWidget(self.stack)
        self.library=LibraryPage(self)
        self.stack.addWidget(self.library)
        self.showFullScreen()

    def go_library(self):
        self.library.refresh()
        self.stack.setCurrentWidget(self.library)

    def open_note(self,path):
        w=NotePage(self,path)
        self.stack.addWidget(w)
        self.stack.setCurrentWidget(w)

    def open_pdf(self,path):
        w=PDFPage(self,path)
        self.stack.addWidget(w)
        self.stack.setCurrentWidget(w)

class USBImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("USB")
        self.resize(440, 700)
        v=QVBoxLayout(self)
        title=QLabel("USB Files")
        title.setObjectName("title")
        v.addWidget(title)
        self.info=QLabel("")
        self.info.setObjectName("muted")
        v.addWidget(self.info)
        self.list=QListWidget()
        v.addWidget(self.list,1)
        self.paths=[]
        for p in scan_importable():
            self.paths.append(p)
            self.list.addItem(f"{p.name}\n{p.parent}")
        buttons=QDialogButtonBox()
        self.import_btn=buttons.addButton("Import",QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Cancel",QDialogButtonBox.ButtonRole.RejectRole)
        self.import_btn.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)
        mounts=usb_mounts()
        self.info.setText(
            f"{len(mounts)} USB drive(s) detected • {len(self.paths)} supported file(s)"
        )
        self.import_btn.setEnabled(bool(self.paths))

    def selected_path(self):
        row=self.list.currentRow()
        if row < 0 and self.paths:
            row=0
        return self.paths[row] if 0 <= row < len(self.paths) else None

class LibraryPage(QWidget):
    def __init__(self,app):
        super().__init__()
        self.app=app
        self._last_usb_count=0
        self.v=QVBoxLayout(self)
        self.v.setContentsMargins(18,16,18,16)
        self.v.setSpacing(12)

        top=QHBoxLayout()
        t=QLabel("Library")
        t.setObjectName("title")
        top.addWidget(t)
        top.addStretch()

        self.usb_btn=QPushButton("USB")
        self.usb_btn.clicked.connect(self.open_usb)
        self.usb_btn.hide()
        top.addWidget(self.usb_btn)
        self.v.addLayout(top)

        actions=QHBoxLayout()
        b=QPushButton("+ Note")
        b.setObjectName("primary")
        b.clicked.connect(self.new_note)
        actions.addWidget(b)

        s=QPushButton("+ Scratch")
        s.clicked.connect(self.new_scratch)
        actions.addWidget(s)

        imp=QPushButton("Import PDF")
        imp.clicked.connect(self.import_pdf)
        actions.addWidget(imp)
        self.v.addLayout(actions)

        self.usb_status=QLabel("")
        self.usb_status.setObjectName("muted")
        self.usb_status.hide()
        self.v.addWidget(self.usb_status)

        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.v.addWidget(self.scroll,1)

        self.usb_timer=QTimer(self)
        self.usb_timer.timeout.connect(self.poll_usb)
        self.usb_timer.start(1200)

        self.refresh()
        self.poll_usb()

    def poll_usb(self):
        mounts=usb_mounts()
        count=len(mounts)
        self.usb_btn.setVisible(count>0)
        self.usb_status.setVisible(count>0)
        if count:
            names=", ".join(p.name for p in mounts)
            self.usb_status.setText(f"USB connected: {names}")
        if count != self._last_usb_count:
            self._last_usb_count=count
            # Do not interrupt reading with a popup; just update the visible indicator.

    def refresh(self):
        host=QWidget()
        g=QGridLayout(host)
        g.setSpacing(12)
        items=list_library()
        if not items:
            empty=QLabel("No books or notes yet.\nCreate a note or connect a USB drive.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(empty,0,0)
        for i,item in enumerate(items):
            label = "BOOK" if item["type"]=="pdf" else ("SCRATCH" if item["type"]=="scratch" else "NOTE")
            card=QPushButton(f"{item['title']}\n\n{label}")
            card.setMinimumSize(190,135)
            if item["type"]=="pdf":
                card.clicked.connect(lambda _,p=item["path"]: self.app.open_pdf(p))
            else:
                card.clicked.connect(lambda _,p=item["path"]: self.app.open_note(p))
            g.addWidget(card,i//2,i%2)
        g.setRowStretch((len(items)+1)//2,1)
        self.scroll.setWidget(host)

    def _create(self,ext,kind):
        title,ok=QInputDialog.getText(self,"New Note","Title:")
        if not ok or not title.strip():
            return
        safe="".join(c for c in title if c not in r'\/:*?"<>|').strip() or "Untitled"
        p=NOTES_DIR/f"{safe}{ext}"
        n=1
        while p.exists():
            p=NOTES_DIR/f"{safe} {n}{ext}"
            n+=1
        save_note(p,title.strip(),[[]],kind)
        self.refresh()
        self.app.open_note(p)

    def new_note(self):
        self._create(".matthew","matthew")

    def new_scratch(self):
        self._create(".matthewscr","scratch")

    def open_usb(self):
        dlg=USBImportDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            src=dlg.selected_path()
            if src:
                try:
                    dest=copy_into_library(src,BOOKS_DIR,NOTES_DIR)
                    self.refresh()
                    QMessageBox.information(self,"Imported",f"Imported {dest.name}")
                except Exception as ex:
                    QMessageBox.warning(self,"Import failed",str(ex))

    def import_pdf(self):
        mounts=usb_mounts()
        start=str(mounts[0]) if mounts else str(Path.home())
        src,_=QFileDialog.getOpenFileName(self,"Import PDF",start,"PDF Files (*.pdf)")
        if not src:
            return
        try:
            dest=copy_into_library(Path(src),BOOKS_DIR,NOTES_DIR)
            self.refresh()
            QMessageBox.information(self,"Imported",f"Imported {dest.name}")
        except Exception as ex:
            QMessageBox.warning(self,"Import failed",str(ex))

class NotePage(QWidget):
    def __init__(self,app,path):
        super().__init__()
        self.app=app
        self.path=Path(path)
        self.manifest,self.pages=load_note(self.path)
        self.page=0

        v=QVBoxLayout(self)
        v.setContentsMargins(8,8,8,8)
        v.setSpacing(6)

        top=QHBoxLayout()
        back=QPushButton("‹")
        back.setFixedWidth(54)
        back.clicked.connect(self.save_and_back)
        top.addWidget(back)
        title=QLabel(self.manifest.get("title",self.path.stem))
        top.addWidget(title)
        top.addStretch()
        self.page_lbl=QLabel()
        top.addWidget(self.page_lbl)
        v.addLayout(top)

        self.canvas=InkCanvas()
        self.canvas.set_page(self.pages[0])
        self.canvas.changed.connect(self.autosave)
        v.addWidget(self.canvas,1)

        bar=QHBoxLayout()
        pen=QPushButton("Pen")
        pen.clicked.connect(lambda:self.canvas.set_tool("pen"))
        bar.addWidget(pen)
        er=QPushButton("Eraser")
        er.clicked.connect(lambda:self.canvas.set_tool("eraser"))
        bar.addWidget(er)
        undo=QPushButton("Undo")
        undo.clicked.connect(self.canvas.undo)
        bar.addWidget(undo)
        prev=QPushButton("‹")
        prev.setFixedWidth(50)
        prev.clicked.connect(self.prev_page)
        bar.addWidget(prev)
        nxt=QPushButton("›")
        nxt.setFixedWidth(50)
        nxt.clicked.connect(self.next_page)
        bar.addWidget(nxt)
        add=QPushButton("+ Page")
        add.clicked.connect(self.add_page)
        bar.addWidget(add)
        v.addLayout(bar)
        self.update_label()

    def autosave(self):
        self.pages[self.page]=self.canvas.strokes
        save_note(
            self.path,
            self.manifest.get("title",self.path.stem),
            self.pages,
            self.manifest.get("kind","matthew")
        )

    def save_and_back(self):
        self.autosave()
        self.app.go_library()

    def update_label(self):
        self.page_lbl.setText(f"{self.page+1}/{len(self.pages)}")

    def show_page(self):
        self.canvas.set_page(self.pages[self.page])
        self.update_label()

    def prev_page(self):
        self.autosave()
        if self.page>0:
            self.page-=1
            self.show_page()

    def next_page(self):
        self.autosave()
        if self.page<len(self.pages)-1:
            self.page+=1
            self.show_page()

    def add_page(self):
        self.autosave()
        self.pages.append([])
        self.page=len(self.pages)-1
        self.show_page()
        self.autosave()

class PDFPage(QWidget):
    def __init__(self,app,path):
        super().__init__()
        self.app=app
        self.path=Path(path)

        v=QVBoxLayout(self)
        v.setContentsMargins(5,5,5,6)
        v.setSpacing(4)

        top=QHBoxLayout()
        back=QPushButton("‹")
        back.setFixedWidth(50)
        back.clicked.connect(app.go_library)
        top.addWidget(back)
        title=QLabel(self.path.stem)
        top.addWidget(title,1)
        self.pg=QLabel()
        top.addWidget(self.pg)
        self.zoom_lbl=QLabel("100%")
        self.zoom_lbl.setObjectName("muted")
        top.addWidget(self.zoom_lbl)
        v.addLayout(top)

        self.viewer=PDFViewer(self.path)
        self.viewer.pageChanged.connect(lambda a,b:self.pg.setText(f"{a}/{b}"))
        self.viewer.zoomChanged.connect(lambda z:self.zoom_lbl.setText(f"{round(z*100)}%"))
        v.addWidget(self.viewer,1)

        # Compact portrait toolbar.
        bar1=QHBoxLayout()
        self.read=QPushButton("Read")
        self.read.clicked.connect(lambda:self.viewer.set_mode("read"))
        bar1.addWidget(self.read)
        self.pen=QPushButton("Pen")
        self.pen.clicked.connect(lambda:self.viewer.set_pen("#222222"))
        bar1.addWidget(self.pen)
        undo=QPushButton("Undo")
        undo.clicked.connect(self.viewer.undo)
        bar1.addWidget(undo)
        reset=QPushButton("100%")
        reset.clicked.connect(self.viewer.reset_zoom)
        bar1.addWidget(reset)
        prev=QPushButton("‹")
        prev.setFixedWidth(48)
        prev.clicked.connect(self.viewer.prev_page)
        bar1.addWidget(prev)
        nxt=QPushButton("›")
        nxt.setFixedWidth(48)
        nxt.clicked.connect(self.viewer.next_page)
        bar1.addWidget(nxt)
        v.addLayout(bar1)

        bar2=QHBoxLayout()
        label=QLabel("Highlight")
        label.setObjectName("muted")
        bar2.addWidget(label)
        for name,c in [("Yellow","yellow"),("Green","green"),("Blue","blue"),("Pink","pink")]:
            b=QPushButton(name)
            b.clicked.connect(lambda _,x=c:self.viewer.set_highlight(x))
            bar2.addWidget(b)
        v.addLayout(bar2)
