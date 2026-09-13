from __future__ import annotations
import fitz
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QImage, QPen, QBrush
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from .storage import load_annotations, save_annotations

HL = {"yellow":"#ffe26a","green":"#9de28f","blue":"#8dccff","pink":"#ff9bc2"}

class PDFViewer(QWidget):
    pageChanged = Signal(int,int)
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.doc = fitz.open(str(path))
        self.page = 0
        self.mode = "read"
        self.pen_color = "#222222"
        self.pen_width = 2.5
        self.highlight_color = "yellow"
        self.anno = load_annotations(path)
        self._img = None
        self._img_rect = QRectF()
        self._current = None
        self._hl_start = None
        self.setMinimumSize(400,500)
        self.render_page()

    def keyPressEvent(self,e):
        if e.key()==Qt.Key.Key_Right: self.next_page()
        elif e.key()==Qt.Key.Key_Left: self.prev_page()

    def render_page(self):
        pg=self.doc.load_page(self.page)
        pix=pg.get_pixmap(matrix=fitz.Matrix(1.7,1.7), alpha=False)
        fmt=QImage.Format.Format_RGB888
        self._img=QImage(pix.samples,pix.width,pix.height,pix.stride,fmt).copy()
        self.update()
        self.pageChanged.emit(self.page+1,len(self.doc))

    def next_page(self):
        if self.page < len(self.doc)-1:
            self.page += 1; self.render_page()
    def prev_page(self):
        if self.page > 0:
            self.page -= 1; self.render_page()

    def set_mode(self, mode): self.mode=mode
    def set_highlight(self,c): self.highlight_color=c; self.mode="highlight"
    def set_pen(self,c="#222222"): self.pen_color=c; self.mode="pen"

    def _page_data(self):
        return self.anno.setdefault("pages",{}).setdefault(str(self.page),{"strokes":[],"highlights":[]})

    def _norm(self,pos):
        r=self._img_rect
        if r.width()<=0 or r.height()<=0: return [0,0]
        return [(pos.x()-r.x())/r.width(),(pos.y()-r.y())/r.height()]
    def _denorm(self,pt):
        r=self._img_rect
        return QPointF(r.x()+pt[0]*r.width(), r.y()+pt[1]*r.height())
    def _inside(self,pos): return self._img_rect.contains(pos)

    def mousePressEvent(self,e):
        if not self._inside(e.position()): return
        if self.mode=="read":
            if e.position().x() > self.width()*0.65: self.next_page()
            elif e.position().x() < self.width()*0.35: self.prev_page()
        elif self.mode=="pen":
            self._current={"color":self.pen_color,"width":self.pen_width,"points":[self._norm(e.position())]}
            self._page_data()["strokes"].append(self._current)
        elif self.mode=="highlight":
            self._hl_start=self._norm(e.position())

    def mouseMoveEvent(self,e):
        if self.mode=="pen" and self._current and self._inside(e.position()):
            self._current["points"].append(self._norm(e.position())); self.update()

    def mouseReleaseEvent(self,e):
        if self.mode=="pen" and self._current:
            if self._inside(e.position()): self._current["points"].append(self._norm(e.position()))
            self._current=None; save_annotations(self.path,self.anno); self.update()
        elif self.mode=="highlight" and self._hl_start and self._inside(e.position()):
            b=self._norm(e.position())
            x1,y1=self._hl_start; x2,y2=b
            self._page_data()["highlights"].append({
                "color":self.highlight_color,
                "rect":[min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)]
            })
            self._hl_start=None; save_annotations(self.path,self.anno); self.update()

    def undo(self):
        d=self._page_data()
        if self.mode=="highlight" and d["highlights"]: d["highlights"].pop()
        elif d["strokes"]: d["strokes"].pop()
        elif d["highlights"]: d["highlights"].pop()
        save_annotations(self.path,self.anno); self.update()

    def paintEvent(self,e):
        p=QPainter(self); p.fillRect(self.rect(),QColor("#e9e7e1"))
        if not self._img: return
        margin=18
        avail=QRectF(margin,margin,self.width()-2*margin,self.height()-2*margin)
        scale=min(avail.width()/self._img.width(), avail.height()/self._img.height())
        w=self._img.width()*scale; h=self._img.height()*scale
        self._img_rect=QRectF((self.width()-w)/2,(self.height()-h)/2,w,h)
        p.drawImage(self._img_rect,self._img)
        d=self._page_data()
        p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        for hlt in d.get("highlights",[]):
            x1,y1,x2,y2=hlt["rect"]; a=self._denorm([x1,y1]); b=self._denorm([x2,y2])
            c=QColor(HL.get(hlt.get("color","yellow"),"#ffe26a")); c.setAlpha(105)
            p.fillRect(QRectF(a,b).normalized(),c)
        for s in d.get("strokes",[]):
            pts=s.get("points",[])
            if len(pts)<2: continue
            p.setPen(QPen(QColor(s.get("color","#222")),float(s.get("width",2.5)),
                          Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
            for a,b in zip(pts,pts[1:]): p.drawLine(self._denorm(a),self._denorm(b))
