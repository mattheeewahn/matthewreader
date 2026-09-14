from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPointF, Signal, QEvent

class InkCanvas(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # IMPORTANT: v2 actually handles QTouchEvent instead of only mouse events.
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setMinimumSize(320, 420)
        self.strokes = []
        self.tool = "pen"
        self.color = "#222222"
        self.pen_width = 2.6
        self.eraser_radius = 28
        self._current = None
        self.setStyleSheet("background:#fbfaf6;")

    def set_page(self, strokes):
        self.strokes = strokes
        self._current = None
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

    def _norm(self, pos: QPointF):
        return [pos.x()/max(1,self.width()), pos.y()/max(1,self.height())]

    def _denorm(self, pt):
        return QPointF(pt[0]*self.width(), pt[1]*self.height())

    def _press(self, pos):
        if self.tool == "eraser":
            self._erase_at(pos)
            return
        self._current = {
            "tool":"pen",
            "color":self.color,
            "width":self.pen_width,
            "points":[self._norm(pos)]
        }
        self.strokes.append(self._current)
        self.update()

    def _move(self, pos):
        if self.tool == "eraser":
            self._erase_at(pos)
            return
        if self._current is not None:
            self._current["points"].append(self._norm(pos))
            self.update()

    def _release(self, pos):
        if self._current is not None:
            self._current["points"].append(self._norm(pos))
            self._current = None
            self.changed.emit()
            self.update()

    def _erase_at(self, pos):
        hit = None
        for i in range(len(self.strokes)-1, -1, -1):
            for pt in self.strokes[i].get("points", []):
                p = self._denorm(pt)
                dx, dy = p.x()-pos.x(), p.y()-pos.y()
                if dx*dx + dy*dy < self.eraser_radius*self.eraser_radius:
                    hit = i
                    break
            if hit is not None:
                break
        if hit is not None:
            self.strokes.pop(hit)
            self.changed.emit()
            self.update()

    def event(self, e):
        t = e.type()
        if t in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate,
                 QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            pts = e.points() if hasattr(e, "points") else e.touchPoints()
            # One-finger writing only. Two fingers are deliberately ignored here.
            if len(pts) == 1:
                pos = pts[0].position()
                if t == QEvent.Type.TouchBegin:
                    self._press(pos)
                elif t == QEvent.Type.TouchUpdate:
                    self._move(pos)
                elif t == QEvent.Type.TouchEnd:
                    self._release(pos)
                else:
                    self._current = None
                e.accept()
                return True
            if len(pts) >= 2:
                self._current = None
                e.accept()
                return True
        return super().event(e)

    # Mouse remains available for USB mouse/testing.
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._move(e.position())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._release(e.position())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#fbfaf6"))
        for s in self.strokes:
            pts = s.get("points", [])
            if len(pts) < 2:
                continue
            pen = QPen(
                QColor(s.get("color", "#222222")),
                float(s.get("width", 2.6)),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            )
            p.setPen(pen)
            for a,b in zip(pts,pts[1:]):
                p.drawLine(self._denorm(a), self._denorm(b))
