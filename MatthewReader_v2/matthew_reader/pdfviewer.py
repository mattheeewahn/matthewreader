from __future__ import annotations
import math
import pymupdf as fitz
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QImage, QPen
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QEvent

HL = {
    "yellow":"#ffe26a",
    "green":"#9de28f",
    "blue":"#8dccff",
    "pink":"#ff9bc2"
}

def _dist(a: QPointF, b: QPointF):
    return math.hypot(a.x()-b.x(), a.y()-b.y())

class PDFViewer(QWidget):
    pageChanged = Signal(int,int)
    zoomChanged = Signal(float)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.path = path
        self.doc = fitz.open(str(path))
        self.page = 0
        self.mode = "read"
        self.pen_color = "#222222"
        self.pen_width = 2.5
        self.highlight_color = "yellow"
        self.anno = self._load_anno()

        self.zoom = 1.0
        self.pan = QPointF(0,0)
        self._img = None
        self._img_rect = QRectF()
        self._render_factor = 1.7

        self._current = None
        self._hl_start = None
        self._hl_preview = None

        self._single_start = None
        self._single_last = None
        self._single_moved = False

        self._pinch = False
        self._pinch_start_distance = 1.0
        self._pinch_start_zoom = 1.0
        self._pinch_start_center = QPointF()
        self._pinch_start_pan = QPointF()

        self.setMinimumSize(320, 400)
        self.render_page()

    def _load_anno(self):
        from .storage import load_annotations
        return load_annotations(self.path)

    def _save(self):
        from .storage import save_annotations
        save_annotations(self.path, self.anno)

    def render_page(self, high_quality=False):
        pg = self.doc.load_page(self.page)
        factor = self._render_factor
        if high_quality:
            factor = max(1.7, min(4.0, 1.5 * self.zoom))
        pix = pg.get_pixmap(matrix=fitz.Matrix(factor, factor), alpha=False)
        self._img = QImage(
            pix.samples, pix.width, pix.height, pix.stride,
            QImage.Format.Format_RGB888
        ).copy()
        self.update()
        self.pageChanged.emit(self.page+1, len(self.doc))

    def _reset_view(self):
        self.zoom = 1.0
        self.pan = QPointF(0,0)
        self.zoomChanged.emit(self.zoom)

    def next_page(self):
        if self.page < len(self.doc)-1:
            self.page += 1
            self._reset_view()
            self.render_page()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._reset_view()
            self.render_page()

    def set_mode(self, mode):
        self.mode = mode

    def set_highlight(self, color):
        self.highlight_color = color
        self.mode = "highlight"

    def set_pen(self, color="#222222"):
        self.pen_color = color
        self.mode = "pen"

    def _page_data(self):
        return self.anno.setdefault("pages",{}).setdefault(
            str(self.page), {"strokes":[],"highlights":[]}
        )

    def _norm(self, pos):
        r = self._img_rect
        if r.width() <= 0 or r.height() <= 0:
            return [0,0]
        return [(pos.x()-r.x())/r.width(), (pos.y()-r.y())/r.height()]

    def _denorm(self, pt):
        r = self._img_rect
        return QPointF(r.x()+pt[0]*r.width(), r.y()+pt[1]*r.height())

    def _inside(self, pos):
        return self._img_rect.contains(pos)

    def _viewport_rect(self):
        m = 10
        return QRectF(m, m, max(1,self.width()-2*m), max(1,self.height()-2*m))

    def _base_draw_size(self):
        if not self._img:
            return 1.0, 1.0
        avail = self._viewport_rect()
        scale = min(avail.width()/self._img.width(), avail.height()/self._img.height())
        return self._img.width()*scale, self._img.height()*scale

    def _clamp_pan(self):
        bw,bh = self._base_draw_size()
        dw,dh = bw*self.zoom, bh*self.zoom
        avail = self._viewport_rect()
        mx = max(0.0, (dw-avail.width())/2.0)
        my = max(0.0, (dh-avail.height())/2.0)
        self.pan.setX(max(-mx, min(mx, self.pan.x())))
        self.pan.setY(max(-my, min(my, self.pan.y())))
        if self.zoom <= 1.001:
            self.pan = QPointF(0,0)

    def set_zoom(self, z):
        self.zoom = max(1.0, min(4.0, float(z)))
        self._clamp_pan()
        self.zoomChanged.emit(self.zoom)
        self.update()

    def reset_zoom(self):
        self._reset_view()
        self.update()

    def _begin_pinch(self, p1, p2):
        self._pinch = True
        self._current = None
        self._hl_start = None
        self._hl_preview = None
        self._pinch_start_distance = max(1.0, _dist(p1,p2))
        self._pinch_start_zoom = self.zoom
        self._pinch_start_center = QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2)
        self._pinch_start_pan = QPointF(self.pan)

    def _update_pinch(self, p1, p2):
        if not self._pinch:
            self._begin_pinch(p1,p2)
        center = QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2)
        ratio = _dist(p1,p2) / self._pinch_start_distance
        new_zoom = max(1.0, min(4.0, self._pinch_start_zoom * ratio))
        # Keep the content under the pinch center approximately anchored.
        wc = QPointF(self.width()/2, self.height()/2)
        scale_ratio = new_zoom / max(0.001, self._pinch_start_zoom)
        start_rel = self._pinch_start_center - wc - self._pinch_start_pan
        self.pan = center - wc - start_rel * scale_ratio
        self.zoom = new_zoom
        self._clamp_pan()
        self.zoomChanged.emit(self.zoom)
        self.update()

    def _end_pinch(self):
        if self._pinch:
            self._pinch = False
            # Re-render at a density appropriate for the final zoom.
            self.render_page(high_quality=True)

    def _pen_press(self, pos):
        if not self._inside(pos):
            return
        self._current = {
            "color":self.pen_color,
            "width":self.pen_width,
            "points":[self._norm(pos)]
        }
        self._page_data()["strokes"].append(self._current)

    def _pen_move(self, pos):
        if self._current and self._inside(pos):
            self._current["points"].append(self._norm(pos))
            self.update()

    def _pen_release(self, pos):
        if self._current:
            if self._inside(pos):
                self._current["points"].append(self._norm(pos))
            self._current = None
            self._save()
            self.update()

    def _hl_press(self, pos):
        if self._inside(pos):
            self._hl_start = self._norm(pos)
            self._hl_preview = self._hl_start

    def _hl_move(self, pos):
        if self._hl_start and self._inside(pos):
            self._hl_preview = self._norm(pos)
            self.update()

    def _hl_release(self, pos):
        if self._hl_start and self._inside(pos):
            b = self._norm(pos)
            x1,y1 = self._hl_start
            x2,y2 = b
            # Ignore accidental tiny taps.
            if abs(x2-x1) > 0.01 or abs(y2-y1) > 0.008:
                self._page_data()["highlights"].append({
                    "color":self.highlight_color,
                    "rect":[min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)]
                })
                self._save()
        self._hl_start = None
        self._hl_preview = None
        self.update()

    def _read_press(self, pos):
        self._single_start = QPointF(pos)
        self._single_last = QPointF(pos)
        self._single_moved = False

    def _read_move(self, pos):
        if self._single_last is None:
            self._read_press(pos)
            return
        delta = pos - self._single_last
        if _dist(pos, self._single_start) > 8:
            self._single_moved = True
        if self.zoom > 1.001:
            self.pan += delta
            self._clamp_pan()
            self.update()
        self._single_last = QPointF(pos)

    def _read_release(self, pos):
        if self._single_start is None:
            return
        dx = pos.x() - self._single_start.x()
        dy = pos.y() - self._single_start.y()
        moved = math.hypot(dx,dy)
        if self.zoom <= 1.001:
            if moved > 65 and abs(dx) > abs(dy)*1.2:
                if dx < 0:
                    self.next_page()
                else:
                    self.prev_page()
            elif moved < 18:
                if pos.x() > self.width()*0.68:
                    self.next_page()
                elif pos.x() < self.width()*0.32:
                    self.prev_page()
        self._single_start = self._single_last = None
        self._single_moved = False

    def event(self, e):
        t = e.type()
        if t in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate,
                 QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            pts = e.points() if hasattr(e, "points") else e.touchPoints()
            positions = [p.position() for p in pts]

            if len(positions) >= 2:
                if t == QEvent.Type.TouchEnd:
                    self._end_pinch()
                else:
                    self._update_pinch(positions[0], positions[1])
                e.accept()
                return True

            # A pinch may end with one remaining contact.
            if self._pinch:
                if t in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel) or len(positions) < 2:
                    self._end_pinch()
                e.accept()
                return True

            if len(positions) == 1:
                pos = positions[0]
                if self.mode == "pen":
                    if t == QEvent.Type.TouchBegin: self._pen_press(pos)
                    elif t == QEvent.Type.TouchUpdate: self._pen_move(pos)
                    elif t == QEvent.Type.TouchEnd: self._pen_release(pos)
                elif self.mode == "highlight":
                    if t == QEvent.Type.TouchBegin: self._hl_press(pos)
                    elif t == QEvent.Type.TouchUpdate: self._hl_move(pos)
                    elif t == QEvent.Type.TouchEnd: self._hl_release(pos)
                else:
                    if t == QEvent.Type.TouchBegin: self._read_press(pos)
                    elif t == QEvent.Type.TouchUpdate: self._read_move(pos)
                    elif t == QEvent.Type.TouchEnd: self._read_release(pos)
                e.accept()
                return True

            if t == QEvent.Type.TouchCancel:
                self._current = None
                self._hl_start = self._hl_preview = None
                self._single_start = self._single_last = None
                self._end_pinch()
                e.accept()
                return True

        return super().event(e)

    # Mouse support for development/testing.
    def mousePressEvent(self,e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos=e.position()
        if self.mode=="pen": self._pen_press(pos)
        elif self.mode=="highlight": self._hl_press(pos)
        else: self._read_press(pos)

    def mouseMoveEvent(self,e):
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        pos=e.position()
        if self.mode=="pen": self._pen_move(pos)
        elif self.mode=="highlight": self._hl_move(pos)
        else: self._read_move(pos)

    def mouseReleaseEvent(self,e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos=e.position()
        if self.mode=="pen": self._pen_release(pos)
        elif self.mode=="highlight": self._hl_release(pos)
        else: self._read_release(pos)

    def undo(self):
        d = self._page_data()
        if self.mode == "highlight" and d["highlights"]:
            d["highlights"].pop()
        elif d["strokes"]:
            d["strokes"].pop()
        elif d["highlights"]:
            d["highlights"].pop()
        self._save()
        self.update()

    def paintEvent(self,e):
        p=QPainter(self)
        p.fillRect(self.rect(), QColor("#e8e6df"))
        if not self._img:
            return

        avail=self._viewport_rect()
        scale=min(avail.width()/self._img.width(), avail.height()/self._img.height())
        w=self._img.width()*scale*self.zoom
        h=self._img.height()*scale*self.zoom
        cx=self.width()/2 + self.pan.x()
        cy=self.height()/2 + self.pan.y()
        self._img_rect=QRectF(cx-w/2, cy-h/2, w, h)

        p.drawImage(self._img_rect, self._img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        d=self._page_data()
        for hlt in d.get("highlights",[]):
            x1,y1,x2,y2=hlt["rect"]
            a=self._denorm([x1,y1]); b=self._denorm([x2,y2])
            c=QColor(HL.get(hlt.get("color","yellow"),"#ffe26a"))
            c.setAlpha(105)
            p.fillRect(QRectF(a,b).normalized(),c)

        if self._hl_start and self._hl_preview:
            x1,y1=self._hl_start; x2,y2=self._hl_preview
            a=self._denorm([x1,y1]); b=self._denorm([x2,y2])
            c=QColor(HL.get(self.highlight_color,"#ffe26a"))
            c.setAlpha(85)
            p.fillRect(QRectF(a,b).normalized(),c)

        for s in d.get("strokes",[]):
            pts=s.get("points",[])
            if len(pts)<2: continue
            # Keep pen visually stable when zooming.
            width=float(s.get("width",2.5)) * max(0.85, min(1.35, self.zoom**0.25))
            p.setPen(QPen(
                QColor(s.get("color","#222")),
                width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            ))
            for a,b in zip(pts,pts[1:]):
                p.drawLine(self._denorm(a),self._denorm(b))
