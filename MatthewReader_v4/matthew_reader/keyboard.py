from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,QTextEdit,QLabel
)
from PySide6.QtCore import Qt, Signal

class TouchKeyboardDialog(QDialog):
    """Self-contained touch keyboard so Matthew never depends on an OS keyboard."""
    def __init__(self, title="Type", initial="", password=False, multiline=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.shift=False
        self.symbols=False
        self.multiline=multiline

        v=QVBoxLayout(self)
        title_lbl=QLabel(title)
        title_lbl.setStyleSheet("font-size:24px;font-weight:600;padding:8px")
        v.addWidget(title_lbl)

        if multiline:
            self.edit=QTextEdit()
            self.edit.setPlainText(initial)
            self.edit.setMinimumHeight(160)
        else:
            self.edit=QLineEdit(initial)
            if password:
                self.edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.edit.setMinimumHeight(52)
        self.edit.setStyleSheet("font-size:22px;background:#fffefa;padding:8px")
        v.addWidget(self.edit)

        self.keys_host=QVBoxLayout()
        v.addLayout(self.keys_host,1)

        actions=QHBoxLayout()
        cancel=QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        done=QPushButton("Done")
        done.setObjectName("primary")
        done.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addStretch()
        actions.addWidget(done)
        v.addLayout(actions)
        self.rebuild()

    def value(self):
        return self.edit.toPlainText() if self.multiline else self.edit.text()

    def _clear_rows(self):
        while self.keys_host.count():
            item=self.keys_host.takeAt(0)
            if item.layout():
                while item.layout().count():
                    w=item.layout().takeAt(0).widget()
                    if w: w.deleteLater()
                item.layout().deleteLater()

    def rebuild(self):
        self._clear_rows()
        if self.symbols:
            rows=["1234567890","@#$%&*()-","_+=/\\:;!?",".,'\"[]{}"]
        else:
            rows=["qwertyuiop","asdfghjkl","zxcvbnm"]

        for idx,row in enumerate(rows):
            h=QHBoxLayout()
            if not self.symbols and idx==2:
                sh=QPushButton("⇧")
                sh.setMinimumHeight(58)
                sh.clicked.connect(self.toggle_shift)
                h.addWidget(sh)
            for ch in row:
                b=QPushButton(ch.upper() if self.shift and ch.isalpha() else ch)
                b.setMinimumHeight(58)
                b.setMinimumWidth(46)
                b.clicked.connect(lambda _,c=ch:self.type_char(c))
                h.addWidget(b)
            if (not self.symbols and idx==2) or (self.symbols and idx==len(rows)-1):
                bs=QPushButton("⌫")
                bs.setMinimumHeight(58)
                bs.clicked.connect(self.backspace)
                h.addWidget(bs)
            self.keys_host.addLayout(h)

        bottom=QHBoxLayout()
        mode=QPushButton("ABC" if self.symbols else "123")
        mode.clicked.connect(self.toggle_symbols)
        space=QPushButton("Space")
        space.setMinimumHeight(58)
        space.clicked.connect(lambda:self.type_char(" "))
        left=QPushButton("←")
        left.clicked.connect(lambda:self.edit_cursor(-1))
        right=QPushButton("→")
        right.clicked.connect(lambda:self.edit_cursor(1))
        enter=QPushButton("Enter")
        enter.clicked.connect(self.enter_key)
        bottom.addWidget(mode)
        bottom.addWidget(left)
        bottom.addWidget(space,1)
        bottom.addWidget(right)
        bottom.addWidget(enter)
        self.keys_host.addLayout(bottom)

    def type_char(self,ch):
        if self.shift and ch.isalpha():
            ch=ch.upper()
            self.shift=False
            self.rebuild()
        self.edit.insertPlainText(ch) if self.multiline else self.edit.insert(ch)

    def backspace(self):
        if self.multiline:
            c=self.edit.textCursor()
            c.deletePreviousChar()
            self.edit.setTextCursor(c)
        else:
            self.edit.backspace()

    def edit_cursor(self,delta):
        if self.multiline:
            c=self.edit.textCursor()
            c.movePosition(c.MoveOperation.Left if delta<0 else c.MoveOperation.Right)
            self.edit.setTextCursor(c)
        else:
            self.edit.setCursorPosition(max(0,min(len(self.edit.text()),self.edit.cursorPosition()+delta)))

    def enter_key(self):
        if self.multiline:self.type_char("\n")
        else:self.accept()

    def toggle_shift(self):
        self.shift=not self.shift
        self.rebuild()

    def toggle_symbols(self):
        self.symbols=not self.symbols
        self.shift=False
        self.rebuild()

def ask_text(parent,title,prompt="",initial="",password=False):
    dlg=TouchKeyboardDialog(title or prompt,initial,password,False,parent)
    ok=dlg.exec()==QDialog.DialogCode.Accepted
    return dlg.value(),ok

def ask_multiline(parent,title,prompt="",initial=""):
    dlg=TouchKeyboardDialog(title or prompt,initial,False,True,parent)
    ok=dlg.exec()==QDialog.DialogCode.Accepted
    return dlg.value(),ok

class TouchLineEdit(QLineEdit):
    """Tap the field to edit it with Matthew's touch keyboard."""
    committed=Signal(str)
    def __init__(self,title="Type",*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.keyboard_title=title
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self,e):
        text,ok=ask_text(self,self.keyboard_title,initial=self.text())
        if ok:
            self.setText(text)
            self.committed.emit(text)
        e.accept()
