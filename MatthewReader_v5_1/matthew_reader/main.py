import sys,os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, Qt
from .app import ReaderWindow

def main():
    os.environ.setdefault("QT_QPA_PLATFORM","wayland")

    # Explicitly ask Qt to turn unhandled touchscreen events into mouse
    # events for ordinary widgets. InkCanvas/PDFViewer still receive native
    # touch events because they explicitly accept and handle touch.
    QCoreApplication.setAttribute(
        Qt.ApplicationAttribute.AA_SynthesizeMouseForUnhandledTouchEvents,
        True
    )

    app=QApplication(sys.argv)
    app.setApplicationName("Matthew Reader")
    w=ReaderWindow()
    return app.exec()

if __name__=="__main__":
    raise SystemExit(main())
