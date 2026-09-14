from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtGui import QCursor,QIcon
from PySide6.QtCore import Qt,QTimer,QEvent,QSize
from .storage import *
from .canvas import InkCanvas
from .pdfviewer import PDFViewer
from .usb import usb_mounts,scan_importable,copy_into_library
from .covers import ensure_pdf_cover
from .exporter import export_note,export_annotated_pdf,copy_export_to_usb
from .keyboard import TouchLineEdit,ask_text,ask_multiline
from .settings import (
    load_settings,save_settings,current_wifi,wifi_networks,connect_wifi,
    set_brightness,device_info,power_action
)

STYLE="""
*{font-family:'DejaVu Sans';font-size:14px;color:#202020}
QMainWindow,QWidget{background:#f5f3ed}
QPushButton{background:#f5f3ed;border:1px solid #bcb8ae;border-radius:6px;padding:7px 9px;min-height:28px}
QPushButton:pressed{background:#dedad0}
QPushButton#primary{background:#202020;color:white;border:none}
QPushButton#danger{background:#7b2020;color:white;border:none}
QLabel#title{font-size:26px;font-weight:600}
QLabel#section{font-size:18px;font-weight:600;padding-top:8px}
QLabel#muted{color:#777268;font-size:12px}
QLineEdit,QComboBox,QListWidget{background:#fffefa;border:1px solid #bbb7ae;border-radius:5px;padding:7px}
QSlider::groove:horizontal{height:6px;background:#d2cec4;border-radius:3px}
QSlider::handle:horizontal{width:24px;margin:-9px 0;background:#202020;border-radius:12px}
"""

class SleepPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:#000;")
        v=QVBoxLayout(self)
        v.addStretch()
        l=QLabel("Tap to wake")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setStyleSheet("color:#777;font-size:18px;background:#000")
        v.addWidget(l)
        v.addStretch()

class ReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.setStyleSheet(STYLE)
        self.setWindowTitle("Matthew")
        self.stack=QStackedWidget()
        self.setCentralWidget(self.stack)

        self.library=LibraryPage(self)
        self.settings_page=SettingsPage(self)
        self.sleep_page=SleepPage()
        self.stack.addWidget(self.library)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.sleep_page)

        self.before_sleep=self.library
        self.in_sleep=False
        self.idle_timer=QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.sleep_now)
        QApplication.instance().installEventFilter(self)
        self.reset_idle_timer()
        self.showFullScreen()

    def eventFilter(self,obj,event):
        et=event.type()

        if et in (QEvent.Type.TouchBegin,QEvent.Type.MouseButtonPress,QEvent.Type.KeyPress):
            if self.in_sleep:
                self.wake()
                return True
            self.reset_idle_timer()

        # Cage/Wayland on some Raspberry Pi touch combinations may deliver
        # Touch events to ordinary Qt widgets without synthesizing the mouse
        # click those widgets expect. Bridge only standard controls here.
        # InkCanvas and PDFViewer are NOT intercepted, so handwriting,
        # panning and two-finger pinch keep their native touch behavior.
        if et==QEvent.Type.TouchBegin and isinstance(obj,QAbstractButton):
            obj.setDown(True)
            event.accept()
            return True

        if et==QEvent.Type.TouchEnd and isinstance(obj,QAbstractButton):
            obj.setDown(False)
            if obj.isEnabled():
                QTimer.singleShot(0,obj.click)
            event.accept()
            return True

        if et==QEvent.Type.TouchEnd and isinstance(obj,QComboBox):
            QTimer.singleShot(0,obj.showPopup)
            event.accept()
            return True

        return super().eventFilter(obj,event)

    def reset_idle_timer(self):
        mins=int(load_settings().get("screen_timeout",10))
        self.idle_timer.stop()
        if mins>0:
            self.idle_timer.start(mins*60*1000)

    def sleep_now(self):
        if self.in_sleep:return
        self.before_sleep=self.stack.currentWidget()
        self.in_sleep=True
        self.stack.setCurrentWidget(self.sleep_page)

    def wake(self):
        self.in_sleep=False
        self.stack.setCurrentWidget(self.before_sleep if self.before_sleep else self.library)
        self.reset_idle_timer()

    def go_library(self):
        self.library.refresh()
        self.stack.setCurrentWidget(self.library)

    def go_settings(self):
        self.settings_page.refresh()
        self.stack.setCurrentWidget(self.settings_page)

    def open_note(self,p):
        mark_opened(p)
        w=NotePage(self,p)
        self.stack.addWidget(w)
        self.stack.setCurrentWidget(w)

    def open_pdf(self,p):
        mark_opened(p)
        w=PDFPage(self,p)
        self.stack.addWidget(w)
        self.stack.setCurrentWidget(w)

class WiFiDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wi-Fi")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        v=QVBoxLayout(self)
        t=QLabel("Wi-Fi")
        t.setObjectName("title")
        v.addWidget(t)
        self.status=QLabel()
        self.status.setObjectName("muted")
        v.addWidget(self.status)
        self.list=QListWidget()
        v.addWidget(self.list,1)
        buttons=QHBoxLayout()
        ref=QPushButton("Refresh")
        ref.clicked.connect(self.refresh)
        close=QPushButton("Close")
        close.clicked.connect(self.accept)
        conn=QPushButton("Connect")
        conn.setObjectName("primary")
        conn.clicked.connect(self.connect_selected)
        buttons.addWidget(ref)
        buttons.addStretch()
        buttons.addWidget(close)
        buttons.addWidget(conn)
        v.addLayout(buttons)
        self.networks=[]
        self.refresh()

    def refresh(self):
        self.status.setText("Connected: "+(current_wifi() or "Not connected"))
        QApplication.processEvents()
        self.networks=wifi_networks()
        self.list.clear()
        for ssid,signal,security in self.networks:
            lock="🔒 " if security and security!="--" else ""
            self.list.addItem(f"{lock}{ssid}   {signal}%")

    def connect_selected(self):
        row=self.list.currentRow()
        if row<0 or row>=len(self.networks):return
        ssid,signal,security=self.networks[row]
        password=""
        if security and security!="--":
            password,ok=ask_text(self,"Wi-Fi Password",initial="",password=True)
            if not ok:return
        self.status.setText(f"Connecting to {ssid}…")
        QApplication.processEvents()
        rc,out,err=connect_wifi(ssid,password)
        if rc==0:
            QMessageBox.information(self,"Wi-Fi",f"Connected to {ssid}.")
            self.refresh()
        else:
            QMessageBox.warning(self,"Wi-Fi",err or out or "Connection failed.")

class SettingsPage(QWidget):
    def __init__(self,app):
        super().__init__()
        self.app=app
        v=QVBoxLayout(self)
        v.setContentsMargins(20,14,20,18)
        v.setSpacing(10)

        top=QHBoxLayout()
        back=QPushButton("‹ Library")
        back.clicked.connect(app.go_library)
        top.addWidget(back)
        title=QLabel("Settings")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()
        v.addLayout(top)

        net=QLabel("Network")
        net.setObjectName("section")
        v.addWidget(net)
        row=QHBoxLayout()
        self.wifi_label=QLabel()
        row.addWidget(self.wifi_label,1)
        wifi=QPushButton("Wi-Fi")
        wifi.clicked.connect(self.open_wifi)
        row.addWidget(wifi)
        v.addLayout(row)

        disp=QLabel("Display")
        disp.setObjectName("section")
        v.addWidget(disp)
        bright_row=QHBoxLayout()
        bright_row.addWidget(QLabel("Brightness"))
        self.brightness=QSlider(Qt.Orientation.Horizontal)
        self.brightness.setRange(5,100)
        self.brightness.valueChanged.connect(self.brightness_preview)
        self.brightness.sliderReleased.connect(self.apply_brightness)
        bright_row.addWidget(self.brightness,1)
        self.brightness_value=QLabel()
        bright_row.addWidget(self.brightness_value)
        v.addLayout(bright_row)

        timeout_row=QHBoxLayout()
        timeout_row.addWidget(QLabel("Screen timeout"))
        self.timeout=QComboBox()
        self.timeout.addItem("Never",0)
        self.timeout.addItem("1 minute",1)
        self.timeout.addItem("5 minutes",5)
        self.timeout.addItem("10 minutes",10)
        self.timeout.addItem("30 minutes",30)
        self.timeout.currentIndexChanged.connect(self.timeout_changed)
        timeout_row.addWidget(self.timeout)
        timeout_row.addStretch()
        v.addLayout(timeout_row)

        dev=QLabel("Device")
        dev.setObjectName("section")
        v.addWidget(dev)
        self.device_label=QLabel()
        self.device_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.addWidget(self.device_label)

        power=QLabel("Power")
        power.setObjectName("section")
        v.addWidget(power)
        pr=QHBoxLayout()
        reboot=QPushButton("Restart")
        reboot.clicked.connect(lambda:self.confirm_power("reboot"))
        shutdown=QPushButton("Power Off")
        shutdown.setObjectName("danger")
        shutdown.clicked.connect(lambda:self.confirm_power("poweroff"))
        pr.addWidget(reboot)
        pr.addWidget(shutdown)
        pr.addStretch()
        v.addLayout(pr)
        v.addStretch()
        self.refresh()

    def refresh(self):
        s=load_settings()
        self.wifi_label.setText("Connected to "+current_wifi() if current_wifi() else "Not connected")
        self.brightness.blockSignals(True)
        self.brightness.setValue(int(s.get("brightness",70)))
        self.brightness.blockSignals(False)
        self.brightness_value.setText(f"{self.brightness.value()}%")
        wanted=int(s.get("screen_timeout",10))
        idx=self.timeout.findData(wanted)
        self.timeout.blockSignals(True)
        self.timeout.setCurrentIndex(max(0,idx))
        self.timeout.blockSignals(False)
        info=device_info()
        self.device_label.setText(
            f"Matthew Reader v5.3\n"
            f"Device name: {info['hostname']}\n"
            f"IP address: {info['ip']}\n"
            f"Storage: {info['storage_free']} GB free / {info['storage_total']} GB total"
        )

    def open_wifi(self):
        WiFiDialog(self).exec()
        self.refresh()

    def brightness_preview(self,v):
        self.brightness_value.setText(f"{v}%")

    def apply_brightness(self):
        v=self.brightness.value()
        rc,out,err=set_brightness(v)
        if rc!=0:
            QMessageBox.warning(self,"Brightness",err or out or "Could not change brightness.")
            return
        s=load_settings();s["brightness"]=v;save_settings(s)

    def timeout_changed(self):
        mins=int(self.timeout.currentData())
        s=load_settings();s["screen_timeout"]=mins;save_settings(s)
        self.app.reset_idle_timer()

    def confirm_power(self,action):
        text="Restart Matthew Reader?" if action=="reboot" else "Power off Matthew Reader?"
        if QMessageBox.question(self,"Power",text)==QMessageBox.StandardButton.Yes:
            rc,out,err=power_action(action)
            if rc!=0:QMessageBox.warning(self,"Power",err or out or "Command failed.")

class LibraryPage(QWidget):
    def __init__(self,app):
        super().__init__();self.app=app
        v=QVBoxLayout(self);v.setContentsMargins(18,14,18,14);v.setSpacing(8)
        top=QHBoxLayout();t=QLabel("Matthew");t.setObjectName("title");top.addWidget(t);top.addStretch()
        self.search=TouchLineEdit("Search Library");self.search.setPlaceholderText("Search library");self.search.committed.connect(lambda _:self.refresh());top.addWidget(self.search,1)
        settings=QPushButton("⚙");settings.setFixedWidth(50);settings.clicked.connect(app.go_settings);top.addWidget(settings)
        new=QPushButton("+ New");new.setObjectName("primary");new.clicked.connect(self.new_menu);top.addWidget(new);v.addLayout(top)

        filters=QHBoxLayout();self.category=QComboBox()
        for label,key in [("All","all"),("Recent","recent"),("Favorites","favorites"),("Textbooks","textbooks"),("Notes","notes"),("Scratch","scratch")]:self.category.addItem(label,key)
        self.category.currentIndexChanged.connect(self.refresh);filters.addWidget(self.category)
        self.subject=QComboBox();self.subject.currentIndexChanged.connect(self.refresh);filters.addWidget(self.subject,1)
        org=QPushButton("Organize");org.clicked.connect(self.organize);filters.addWidget(org);v.addLayout(filters)

        self.usb=QLabel("");self.usb.setObjectName("muted");v.addWidget(self.usb)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.Shape.NoFrame);v.addWidget(self.scroll,1)
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll_usb);self.timer.start(1200)
        self.refresh_subjects();self.refresh();self.poll_usb()

    def poll_usb(self):
        m=usb_mounts();self.usb.setText(("USB: "+", ".join(x.name for x in m)) if m else "")

    def refresh_subjects(self):
        cur=self.subject.currentData() if self.subject.count() else ""
        self.subject.blockSignals(True);self.subject.clear();self.subject.addItem("All subjects","")
        for s in subjects():self.subject.addItem(s,s)
        idx=self.subject.findData(cur);self.subject.setCurrentIndex(max(0,idx));self.subject.blockSignals(False)

    def refresh(self,*_):
        if not hasattr(self,"scroll"):return
        host=QWidget();g=QGridLayout(host);g.setSpacing(14)
        items=list_library(self.search.text(),self.category.currentData(),self.subject.currentData())
        if not items:
            empty=QLabel("No documents in this view.");empty.setAlignment(Qt.AlignmentFlag.AlignCenter);g.addWidget(empty,0,0)
        for i,it in enumerate(items):
            frame=QFrame();frame.setObjectName("card");lv=QVBoxLayout(frame);lv.setContentsMargins(6,6,6,6);lv.setSpacing(4)
            card=QToolButton();card.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon);card.setText(it["title"]);card.setMinimumSize(210,220)
            if it["type"]=="pdf":
                cp=ensure_pdf_cover(it["path"])
                if cp:card.setIcon(QIcon(str(cp)));card.setIconSize(QSize(128,166))
                card.clicked.connect(lambda _,p=it["path"]:self.app.open_pdf(p))
            else:
                card.setText(f"{it['title']}\n\n{it['type'].upper()}")
                card.clicked.connect(lambda _,p=it["path"]:self.app.open_note(p))
            lv.addWidget(card,1)
            foot=QHBoxLayout();sub=QLabel(it.get("subject") or ("Textbook" if it["type"]=="pdf" else it["type"].title()));sub.setObjectName("muted");foot.addWidget(sub,1)
            star=QPushButton("★" if it.get("favorite") else "☆");star.setFixedWidth(46);star.clicked.connect(lambda _,p=it["path"]:self.favorite(p));foot.addWidget(star);lv.addLayout(foot)
            g.addWidget(frame,i//2,i%2)
        g.setRowStretch((len(items)+1)//2,1);self.scroll.setWidget(host)

    def favorite(self,path):toggle_favorite(path);self.refresh()

    def organize(self):
        items=list_library();
        if not items:QMessageBox.information(self,"Organize","No documents yet.");return
        labels=[f"{x['title']}  [{x['type']}]" for x in items];choice,ok=QInputDialog.getItem(self,"Organize","Document:",labels,0,False)
        if not ok:return
        item=items[labels.index(choice)];existing=subjects();choices=["No subject"]+existing+["+ New subject…"]
        sub,ok=QInputDialog.getItem(self,"Subject","Move to:",choices,0,False)
        if not ok:return
        if sub=="+ New subject…":
            sub,ok=ask_text(self,"New Subject")
            if not ok:return
        if sub=="No subject":sub=""
        set_subject(item["path"],sub);self.refresh_subjects();self.refresh()

    def new_menu(self):
        m=QMenu(self);m.addAction("Notebook",lambda:self.create_note(".matthew","matthew"));m.addAction("Scratch Note",lambda:self.create_note(".matthewscr","scratch"));m.addSeparator();m.addAction("Import from USB",self.import_usb);m.addAction("Import PDF",self.import_pdf);m.exec(QCursor.pos())

    def create_note(self,ext,kind):
        name,ok=ask_text(self,"New Notebook")
        if not ok or not name.strip():return
        templates=["blank","lined","grid","dotted","cornell"];tmpl,ok=QInputDialog.getItem(self,"Paper","Template:",templates,0,False)
        if not ok:return
        safe="".join(c for c in name if c not in r'\/:*?"<>|').strip();p=NOTES_DIR/f"{safe}{ext}";n=1
        while p.exists():p=NOTES_DIR/f"{safe} {n}{ext}";n+=1
        save_note(p,name.strip(),[[]],kind,tmpl);self.refresh();self.app.open_note(p)

    def import_usb(self):
        files=scan_importable()
        if not files:QMessageBox.information(self,"USB","No supported files found.");return
        names=[str(p) for p in files];choice,ok=QInputDialog.getItem(self,"USB Import","File:",names,0,False)
        if ok and choice:copy_into_library(Path(choice),BOOKS_DIR,NOTES_DIR);self.refresh()

    def import_pdf(self):
        start=str(usb_mounts()[0]) if usb_mounts() else str(Path.home());f,_=QFileDialog.getOpenFileName(self,"Import PDF",start,"PDF (*.pdf)")
        if f:copy_into_library(Path(f),BOOKS_DIR,NOTES_DIR);self.refresh()


def choose_export(parent,created):
    mounts=usb_mounts();opts=["Internal Exports"]+[f"USB: {m.name}" for m in mounts]
    choice,ok=QInputDialog.getItem(parent,"Export","Destination:",opts,0,False)
    if not ok:return None
    if choice.startswith("USB:"):
        mount=mounts[opts.index(choice)-1];return copy_export_to_usb(created,mount)
    return created

class NotePage(QWidget):
    def __init__(self,app,path):
        super().__init__();self.app=app;self.path=Path(path);self.manifest,self.pages=load_note(self.path);self.page=0;self.template=self.manifest.get("template","blank")
        v=QVBoxLayout(self);v.setContentsMargins(6,5,6,6);v.setSpacing(4)
        nav=QHBoxLayout();back=QPushButton("‹ Library");back.clicked.connect(self.back);nav.addWidget(back);nav.addWidget(QLabel(self.manifest.get("title",self.path.stem)),1);self.page_lbl=QLabel();nav.addWidget(self.page_lbl)
        exp=QPushButton("Export PDF");exp.clicked.connect(self.export_pdf);nav.addWidget(exp);v.addLayout(nav)
        self.canvas=InkCanvas()

        tools=QHBoxLayout()
        for label,tool in [("Pen","pen"),("Highlighter","highlighter"),("Eraser","eraser"),("Lasso","lasso"),("Text","text"),("Auto Shape","autoshape")]:
            b=QPushButton(label);b.clicked.connect(lambda _,t=tool:self.canvas.set_tool(t));tools.addWidget(b)
        v.addLayout(tools)
        shapes=QHBoxLayout();shapes.addWidget(QLabel("Shapes"))
        for label,tool in [("Line","line"),("Rect","rectangle"),("Circle","ellipse"),("Triangle","triangle"),("Arrow","arrow")]:
            b=QPushButton(label);b.clicked.connect(lambda _,t=tool:self.canvas.set_tool(t));shapes.addWidget(b)
        v.addLayout(shapes)

        presets=QHBoxLayout();presets.addWidget(QLabel("Presets"))
        for label,tool,c,w in [("P1","pen","#202020",2.0),("P2","pen","#2855d9",2.6),("P3","pen","#d64242",3.2),("H","highlighter","#ffe26a",3.0)]:
            b=QPushButton(label);b.clicked.connect(lambda _,t=tool,col=c,wd=w:self.canvas.set_preset(t,col,wd));presets.addWidget(b)
        presets.addStretch();v.addLayout(presets)

        opts=QHBoxLayout()
        for label,c in [("Black","#202020"),("Blue","#2855d9"),("Red","#d64242")]:
            b=QPushButton(label);b.clicked.connect(lambda _,x=c:self.canvas.set_color(x));opts.addWidget(b)
        width=QComboBox();width.addItems(["1.5","2.6","4.0","6.0"]);width.setCurrentText("2.6");width.currentTextChanged.connect(lambda x:self.canvas.set_width(float(x)));opts.addWidget(width)
        u=QPushButton("Undo");u.clicked.connect(self.canvas.undo);opts.addWidget(u);r=QPushButton("Redo");r.clicked.connect(self.canvas.redo);opts.addWidget(r);d=QPushButton("Delete");d.clicked.connect(self.canvas.delete_selection);opts.addWidget(d);v.addLayout(opts)

        self.canvas.set_page(self.pages[0],self.template);self.canvas.changed.connect(self.save);self.canvas.textRequested.connect(self.add_text);v.addWidget(self.canvas,1)
        foot=QHBoxLayout();pr=QPushButton("‹");pr.clicked.connect(self.prev);foot.addWidget(pr);go=QPushButton("Go to page");go.clicked.connect(self.goto);foot.addWidget(go);nx=QPushButton("›");nx.clicked.connect(self.next);foot.addWidget(nx);add=QPushButton("+ Page");add.clicked.connect(self.add_page);foot.addWidget(add);foot.addStretch();v.addLayout(foot);self.label()

    def add_text(self,x,y):
        text,ok=ask_multiline(self,"Insert Text")
        if ok:self.canvas.add_text(x,y,text)
    def save(self):self.pages[self.page]=self.canvas.objects;save_note(self.path,self.manifest.get("title",self.path.stem),self.pages,self.manifest.get("kind","matthew"),self.template)
    def back(self):self.save();self.app.go_library()
    def label(self):self.page_lbl.setText(f"{self.page+1}/{len(self.pages)}")
    def showp(self):self.canvas.set_page(self.pages[self.page],self.template);self.label()
    def prev(self):self.save();self.page=max(0,self.page-1);self.showp()
    def next(self):self.save();self.page=min(len(self.pages)-1,self.page+1);self.showp()
    def add_page(self):self.save();self.pages.append([]);self.page=len(self.pages)-1;self.showp();self.save()
    def goto(self):
        text,ok=ask_text(self,"Go to Page",initial=str(self.page+1))
        if not ok:return
        try:n=int(text)
        except ValueError:return
        if 1<=n<=len(self.pages):self.save();self.page=n-1;self.showp()
    def export_pdf(self):
        self.save()
        try:
            created=export_note(self.path);dest=choose_export(self,created)
            if dest:QMessageBox.information(self,"Export",f"Exported to:\n{dest}")
        except Exception as e:QMessageBox.warning(self,"Export failed",str(e))

class PDFPage(QWidget):
    def __init__(self,app,path):
        super().__init__();self.app=app;self.path=Path(path);v=QVBoxLayout(self);v.setContentsMargins(5,5,5,5);v.setSpacing(4)
        nav=QHBoxLayout();back=QPushButton("‹ Library");back.clicked.connect(app.go_library);nav.addWidget(back);nav.addWidget(QLabel(self.path.stem),1);self.pg=QLabel();nav.addWidget(self.pg);self.zoom=QLabel();self.zoom.setObjectName("muted");nav.addWidget(self.zoom)
        go=QPushButton("Go");go.clicked.connect(self.goto_page);nav.addWidget(go);exp=QPushButton("Export");exp.clicked.connect(self.export_pdf);nav.addWidget(exp);v.addLayout(nav)
        self.viewer=PDFViewer(self.path)
        tools=QHBoxLayout()
        for label,fn in [("Read",lambda:self.viewer.set_mode("read")),("Pen",lambda:self.viewer.set_pen()),("Undo",self.viewer.undo),("TOC",self.show_toc),("Search",self.search_pdf),("Bookmark",self.bookmark)]:
            b=QPushButton(label);b.clicked.connect(fn);tools.addWidget(b)
        reset=QPushButton("100%");reset.clicked.connect(self.viewer.reset_zoom);tools.addWidget(reset);v.addLayout(tools)

        presets=QHBoxLayout();presets.addWidget(QLabel("Pen"))
        for label,c,w in [("P1","#202020",2.0),("P2","#2855d9",2.6),("P3","#d64242",3.2)]:
            b=QPushButton(label);b.clicked.connect(lambda _,col=c,wd=w:self.viewer.set_pen(col,wd));presets.addWidget(b)
        presets.addWidget(QLabel("Highlight"))
        for label,c in [("Y","yellow"),("G","green"),("B","blue"),("P","pink")]:
            b=QPushButton(label);b.clicked.connect(lambda _,x=c:self.viewer.set_highlight(x));presets.addWidget(b)
        bm=QPushButton("Bookmarks");bm.clicked.connect(self.show_bookmarks);presets.addWidget(bm);presets.addStretch();v.addLayout(presets)

        self.viewer.pageChanged.connect(lambda a,b:self.pg.setText(f"{a}/{b}"));self.viewer.zoomChanged.connect(lambda z:self.zoom.setText(f"{round(z*100)}%"));v.addWidget(self.viewer,1)
        self.pg.setText(f"{self.viewer.page+1}/{len(self.viewer.doc)}");self.zoom.setText(f"{round(self.viewer.zoom*100)}%")

    def goto_page(self):
        text,ok=ask_text(self,"Go to Page",initial=str(self.viewer.page+1))
        if not ok:return
        try:n=int(text)
        except ValueError:return
        if 1<=n<=len(self.viewer.doc):self.viewer.goto_page(n-1)
        else:QMessageBox.warning(self,"Page",f"Enter a page from 1 to {len(self.viewer.doc)}.")
    def show_toc(self):
        toc=self.viewer.toc()
        if not toc:QMessageBox.information(self,"Contents","This PDF has no embedded table of contents.");return
        labels=[("  "*(lvl-1))+title for lvl,title,page,*_ in toc];choice,ok=QInputDialog.getItem(self,"Contents","Chapter:",labels,0,False)
        if ok:self.viewer.goto_page(max(0,toc[labels.index(choice)][2]-1))
    def search_pdf(self):
        q,ok=ask_text(self,"Search PDF")
        if not ok or not q:return
        hits=self.viewer.search(q)
        if not hits:QMessageBox.information(self,"Search","No results.");return
        labels=[f"p. {p+1} — {s[:100]}" for p,s in hits];choice,ok=QInputDialog.getItem(self,"Search results","Result:",labels,0,False)
        if ok:self.viewer.goto_page(hits[labels.index(choice)][0])
    def bookmark(self):
        self.viewer.toggle_bookmark();QMessageBox.information(self,"Bookmark","Bookmark "+("added." if self.viewer.is_bookmarked() else "removed."))
    def show_bookmarks(self):
        pages=self.viewer.bookmarks()
        if not pages:QMessageBox.information(self,"Bookmarks","No bookmarks.");return
        labels=[f"Page {p+1}" for p in pages];choice,ok=QInputDialog.getItem(self,"Bookmarks","Go to:",labels,0,False)
        if ok:self.viewer.goto_page(pages[labels.index(choice)])
    def export_pdf(self):
        try:
            self.viewer.persist();created=export_annotated_pdf(self.path);dest=choose_export(self,created)
            if dest:QMessageBox.information(self,"Export",f"Exported to:\n{dest}")
        except Exception as e:QMessageBox.warning(self,"Export failed",str(e))
