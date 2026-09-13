from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtCore import Qt, QPointF, QRectF, Signal

class InkCanvas(QWidget):
    changed = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setMinimumSize(400, 500)
        self.strokes = []
        self.tool = "pen"
        self.color = "#222222"
        self.width = 2.6
        self._current = None
        self.setStyleSheet("background:#fbfaf6;")

    def set_page(self, strokes):
        self.strokes = strokes
        self.update()

    def set_tool(self, tool):
        self.tool = tool

    def set_color(self, color):
        self.color = color

    def undo(self):
        if self.strokes:
            self.strokes.pop()
            self.changed.emit()
            self.update()

    def clear_page(self):
        self.strokes.clear()
        self.changed.emit()
        self.update()

    def _norm(self, pos):
        return [pos.x()/max(1,self.width()), pos.y()/max(1,self.height())]

    def _denorm(self, pt):
        return QPointF(pt[0]*self.width(), pt[1]*self.height())

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton: return
        if self.tool == "eraser":
            self._erase_at(e.position()); return
        self._current = {"tool":"pen","color":self.color,"width":self.width,"points":[self._norm(e.position())]}
        self.strokes.append(self._current)
        self.update()

    def mouseMoveEvent(self, e):
        if self.tool == "eraser":
            self._erase_at(e.position()); return
        if self._current is not None:
            self._current["points"].append(self._norm(e.position()))
            self.update()

    def mouseReleaseEvent(self, e):
        if self._current is not None:
            self._current["points"].append(self._norm(e.position()))
            self._current = None
            self.changed.emit()
            self.update()

    def _erase_at(self, pos):
        radius = 24
        hit = None
        for i in range(len(self.strokes)-1, -1, -1):
            for pt in self.strokes[i].get("points",[]):
                if (self._denorm(pt)-pos).manhattanLength() < radius:
                    hit=i; break
            if hit is not None: break
        if hit is not None:
            self.strokes.pop(hit); self.changed.emit(); self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#fbfaf6"))
        for s in self.strokes:
            pts=s.get("points",[])
            if len(pts)<2: continue
            pen=QPen(QColor(s.get("color","#222")), float(s.get("width",2.6)),
                     Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            for a,b in zip(pts,pts[1:]):
                p.drawLine(self._denorm(a),self._denorm(b))
