import sys, os
from PySide6.QtWidgets import QApplication
from .app import ReaderWindow

def main():
    os.environ.setdefault("QT_QPA_PLATFORM","wayland")
    app=QApplication(sys.argv)
    app.setApplicationName("Matthew Reader")
    w=ReaderWindow()
    return app.exec()

if __name__=="__main__":
    raise SystemExit(main())
