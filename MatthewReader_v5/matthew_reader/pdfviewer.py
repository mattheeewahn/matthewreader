from __future__ import annotations
import math
import pymupdf as fitz
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter,QColor,QImage,QPen
from PySide6.QtCore import Qt,QPointF,QRectF,Signal,QEvent
from .storage import load_annotations,save_annotations,document_state,update_document_state

HL={"yellow":"#ffe26a","green":"#9de28f","blue":"#8dccff","pink":"#ff9bc2"}
def dist(a,b):return math.hypot(a.x()-b.x(),a.y()-b.y())

class PDFViewer(QWidget):
    pageChanged=Signal(int,int)
    zoomChanged=Signal(float)

    def __init__(self,path,parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents,True)
        self.path=path;self.doc=fitz.open(str(path));self.anno=load_annotations(path)
        st=document_state(path)
        self.page=max(0,min(int(st.get("page",0)),len(self.doc)-1))
        self.zoom=max(1.0,min(float(st.get("zoom",1.0)),4.0))
        self.pan=QPointF();self.mode="read";self.pen_color="#202020";self.pen_width=2.5;self.highlight_color="yellow"
        self.img=None;self.img_rect=QRectF();self.current=None;self.hl_start=None;self.hl_preview=None
        self.single_start=None;self.single_last=None;self.pinch=False;self.pinch_d=1;self.pinch_z=1;self.pinch_c=QPointF();self.pinch_p=QPointF()
        self.render_page()

    def pd(self):return self.anno.setdefault("pages",{}).setdefault(str(self.page),{"strokes":[],"highlights":[]})
    def persist(self):
        save_annotations(self.path,self.anno);update_document_state(self.path,page=self.page,zoom=self.zoom)

    def render_page(self):
        factor=max(1.7,min(4.0,1.4*self.zoom))
        pix=self.doc.load_page(self.page).get_pixmap(matrix=fitz.Matrix(factor,factor),alpha=False)
        self.img=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
        self.update();self.pageChanged.emit(self.page+1,len(self.doc));self.persist()

    def goto_page(self,p):
        self.page=max(0,min(int(p),len(self.doc)-1));self.zoom=1.0;self.pan=QPointF();self.render_page()

    def next_page(self):
        if self.page<len(self.doc)-1:self.goto_page(self.page+1)
    def prev_page(self):
        if self.page>0:self.goto_page(self.page-1)

    def set_mode(self,m):self.mode=m
    def set_pen(self,c="#202020",width=None):
        self.pen_color=c
        if width is not None:self.pen_width=float(width)
        self.mode="pen"
    def set_highlight(self,c):self.highlight_color=c;self.mode="highlight"

    def toc(self):return self.doc.get_toc(simple=True)
    def search(self,text,limit=100):
        text=text.strip();out=[]
        if not text:return out
        for i in range(len(self.doc)):
            pg=self.doc.load_page(i)
            if pg.search_for(text):
                snippet=" ".join(pg.get_text("text").split())[:160]
                out.append((i,snippet))
                if len(out)>=limit:break
        return out

    def toggle_bookmark(self):
        b=self.anno.setdefault("bookmarks",[])
        if self.page in b:b.remove(self.page)
        else:b.append(self.page);b.sort()
        self.persist()
    def is_bookmarked(self):return self.page in self.anno.setdefault("bookmarks",[])
    def bookmarks(self):return list(self.anno.setdefault("bookmarks",[]))

    def undo(self):
        d=self.pd()
        if self.mode=="highlight" and d["highlights"]:d["highlights"].pop()
        elif d["strokes"]:d["strokes"].pop()
        elif d["highlights"]:d["highlights"].pop()
        self.persist();self.update()

    def norm(self,p):
        r=self.img_rect
        return [(p.x()-r.x())/max(1,r.width()),(p.y()-r.y())/max(1,r.height())]
    def denorm(self,p):
        r=self.img_rect;return QPointF(r.x()+p[0]*r.width(),r.y()+p[1]*r.height())
    def inside(self,p):return self.img_rect.contains(p)

    def base(self):
        if not self.img:return (1,1)
        a=QRectF(8,8,max(1,self.width()-16),max(1,self.height()-16))
        s=min(a.width()/self.img.width(),a.height()/self.img.height())
        return self.img.width()*s,self.img.height()*s

    def clamp(self):
        bw,bh=self.base();dw,dh=bw*self.zoom,bh*self.zoom
        mx=max(0,(dw-(self.width()-16))/2);my=max(0,(dh-(self.height()-16))/2)
        self.pan.setX(max(-mx,min(mx,self.pan.x())));self.pan.setY(max(-my,min(my,self.pan.y())))
        if self.zoom<=1.001:self.pan=QPointF()

    def reset_zoom(self):
        self.zoom=1;self.pan=QPointF();self.zoomChanged.emit(self.zoom);self.render_page()

    def begin_pinch(self,a,b):
        self.pinch=True;self.current=None;self.hl_start=None
        self.pinch_d=max(1,dist(a,b));self.pinch_z=self.zoom;self.pinch_c=(a+b)/2;self.pinch_p=QPointF(self.pan)

    def move_pinch(self,a,b):
        if not self.pinch:self.begin_pinch(a,b)
        c=(a+b)/2;ratio=dist(a,b)/self.pinch_d;nz=max(1,min(4,self.pinch_z*ratio))
        wc=QPointF(self.width()/2,self.height()/2);rel=self.pinch_c-wc-self.pinch_p;sr=nz/max(.001,self.pinch_z)
        self.pan=c-wc-rel*sr;self.zoom=nz;self.clamp();self.zoomChanged.emit(self.zoom);self.update()

    def press(self,p):
        if self.mode=="pen" and self.inside(p):
            self.current={"color":self.pen_color,"width":self.pen_width,"points":[self.norm(p)]};self.pd()["strokes"].append(self.current)
        elif self.mode=="highlight" and self.inside(p):
            self.hl_start=self.norm(p);self.hl_preview=self.hl_start
        else:
            self.single_start=QPointF(p);self.single_last=QPointF(p)

    def move(self,p):
        if self.mode=="pen" and self.current and self.inside(p):
            self.current["points"].append(self.norm(p));self.update()
        elif self.mode=="highlight" and self.hl_start and self.inside(p):
            self.hl_preview=self.norm(p);self.update()
        elif self.single_last is not None and self.zoom>1:
            d=p-self.single_last;self.pan+=d;self.single_last=QPointF(p);self.clamp();self.update()

    def release(self,p):
        if self.mode=="pen" and self.current:
            if self.inside(p):self.current["points"].append(self.norm(p))
            self.current=None;self.persist();self.update()
        elif self.mode=="highlight" and self.hl_start:
            if self.inside(p):
                x1,y1=self.hl_start;x2,y2=self.norm(p)
                if abs(x2-x1)>.01 or abs(y2-y1)>.008:
                    self.pd()["highlights"].append({"color":self.highlight_color,"rect":[min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)]})
            self.hl_start=self.hl_preview=None;self.persist();self.update()
        elif self.single_start is not None:
            dx=p.x()-self.single_start.x();dy=p.y()-self.single_start.y();m=math.hypot(dx,dy)
            if self.zoom<=1.001:
                if m>65 and abs(dx)>abs(dy)*1.2:
                    self.next_page() if dx<0 else self.prev_page()
                elif m<18:
                    if p.x()>self.width()*.68:self.next_page()
                    elif p.x()<self.width()*.32:self.prev_page()
            self.single_start=self.single_last=None

    def event(self,e):
        t=e.type()
        if t in (QEvent.Type.TouchBegin,QEvent.Type.TouchUpdate,QEvent.Type.TouchEnd,QEvent.Type.TouchCancel):
            pts=e.points() if hasattr(e,"points") else e.touchPoints();ps=[x.position() for x in pts]
            if len(ps)>=2:
                if t==QEvent.Type.TouchEnd:self.pinch=False;self.render_page()
                else:self.move_pinch(ps[0],ps[1])
                e.accept();return True
            if self.pinch:
                if t in (QEvent.Type.TouchEnd,QEvent.Type.TouchCancel) or len(ps)<2:self.pinch=False;self.render_page()
                e.accept();return True
            if len(ps)==1:
                if t==QEvent.Type.TouchBegin:self.press(ps[0])
                elif t==QEvent.Type.TouchUpdate:self.move(ps[0])
                elif t==QEvent.Type.TouchEnd:self.release(ps[0])
                e.accept();return True
        return super().event(e)

    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:self.press(e.position())
    def mouseMoveEvent(self,e):
        if e.buttons()&Qt.MouseButton.LeftButton:self.move(e.position())
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:self.release(e.position())

    def paintEvent(self,e):
        p=QPainter(self);p.fillRect(self.rect(),QColor("#e9e7e1"))
        if not self.img:return
        bw,bh=self.base();w,h=bw*self.zoom,bh*self.zoom;cx=self.width()/2+self.pan.x();cy=self.height()/2+self.pan.y()
        self.img_rect=QRectF(cx-w/2,cy-h/2,w,h);p.drawImage(self.img_rect,self.img);p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        d=self.pd()
        for hlt in d["highlights"]:
            a=self.denorm(hlt["rect"][:2]);b=self.denorm(hlt["rect"][2:]);c=QColor(HL.get(hlt["color"],"#ffe26a"));c.setAlpha(100)
            p.fillRect(QRectF(a,b).normalized(),c)
        if self.hl_start and self.hl_preview:
            a=self.denorm(self.hl_start);b=self.denorm(self.hl_preview);c=QColor(HL.get(self.highlight_color,"#ffe26a"));c.setAlpha(80)
            p.fillRect(QRectF(a,b).normalized(),c)
        for s in d["strokes"]:
            pts=s.get("points",[])
            if len(pts)<2:continue
            p.setPen(QPen(QColor(s.get("color","#202020")),float(s.get("width",2.5)),Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
            for a,b in zip(pts,pts[1:]):p.drawLine(self.denorm(a),self.denorm(b))
