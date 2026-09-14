from __future__ import annotations
import copy, math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter,QPen,QColor,QFont,QPolygonF
from PySide6.QtCore import Qt,QPointF,QRectF,Signal,QEvent

class InkCanvas(QWidget):
    changed=Signal(); textRequested=Signal(float,float)
    def __init__(self,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents,True)
        self.objects=[];self.tool="pen";self.color="#202020";self.pen_width=2.6;self.template="blank"
        self.current=None;self.start=None;self.lasso=None;self.selected=[];self.moving=False;self.move_last=None
        self.undo_stack=[];self.redo_stack=[]
    def set_page(self,objects,template="blank"):
        self.objects=objects;self.template=template;self.selected=[];self.current=None;self.undo_stack=[];self.redo_stack=[];self.update()
    def snapshot(self):
        self.undo_stack.append(copy.deepcopy(self.objects));self.redo_stack.clear()
        if len(self.undo_stack)>80:self.undo_stack.pop(0)
    def undo(self):
        if not self.undo_stack:return
        self.redo_stack.append(copy.deepcopy(self.objects));self.objects[:]=self.undo_stack.pop();self.selected=[];self.changed.emit();self.update()
    def redo(self):
        if not self.redo_stack:return
        self.undo_stack.append(copy.deepcopy(self.objects));self.objects[:]=self.redo_stack.pop();self.selected=[];self.changed.emit();self.update()
    def set_tool(self,t):self.tool=t
    def set_color(self,c):self.color=c
    def set_width(self,w):self.pen_width=float(w)
    def set_preset(self,tool,color,width):self.tool=tool;self.color=color;self.pen_width=float(width)
    def norm(self,p):return [p.x()/max(1,self.width()),p.y()/max(1,self.height())]
    def denorm(self,p):return QPointF(p[0]*self.width(),p[1]*self.height())
    def bbox(self,o):
        typ=o.get("type","stroke")
        if typ=="stroke":
            pts=o.get("points",[])
            if not pts:return QRectF()
            xs=[x*self.width() for x,y in pts];ys=[y*self.height() for x,y in pts]
            return QRectF(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)).adjusted(-8,-8,8,8)
        if typ=="text":return QRectF(o["x"]*self.width(),o["y"]*self.height()-24,max(60,len(o.get("text",""))*10),34)
        if typ=="shape":return QRectF(self.denorm(o["a"]),self.denorm(o["b"])).normalized().adjusted(-10,-10,10,10)
        return QRectF()
    def add_text(self,x,y,text):
        if not text:return
        self.snapshot();self.objects.append({"type":"text","x":x,"y":y,"text":text,"color":self.color,"size":18});self.changed.emit();self.update()
    def delete_selection(self):
        if not self.selected:return
        self.snapshot();sel=set(self.selected);self.objects[:]=[o for i,o in enumerate(self.objects) if i not in sel];self.selected=[];self.changed.emit();self.update()
    def erase(self,pos):
        for i in range(len(self.objects)-1,-1,-1):
            if self.bbox(self.objects[i]).contains(pos):
                self.snapshot();self.objects.pop(i);self.changed.emit();self.update();return
    def _make_shape(self,shape,pos):
        self.snapshot();self.current={"type":"shape","shape":shape,"a":self.norm(pos),"b":self.norm(pos),"color":self.color,"width":self.pen_width};self.objects.append(self.current)
    def press(self,pos):
        if self.tool=="eraser":self.erase(pos);return
        if self.tool=="text":
            x,y=self.norm(pos);self.textRequested.emit(x,y);return
        if self.tool=="lasso":
            if self.selected:
                r=QRectF()
                for i in self.selected:r=r.united(self.bbox(self.objects[i]))
                if r.adjusted(-12,-12,12,12).contains(pos):self.snapshot();self.moving=True;self.move_last=QPointF(pos);return
            self.start=QPointF(pos);self.lasso=QRectF(pos,pos);self.selected=[];self.update();return
        if self.tool in ("line","rectangle","ellipse","triangle","arrow"):
            self._make_shape(self.tool,pos);return
        self.snapshot();self.current={"type":"stroke","tool":"highlighter" if self.tool=="highlighter" else ("autoshape" if self.tool=="autoshape" else "pen"),"color":self.color,"width":self.pen_width*(5 if self.tool=="highlighter" else 1),"points":[self.norm(pos)]};self.objects.append(self.current);self.update()
    def move(self,pos):
        if self.tool=="eraser":self.erase(pos);return
        if self.tool=="lasso":
            if self.moving:
                d=pos-self.move_last;self.move_last=QPointF(pos);dx=d.x()/max(1,self.width());dy=d.y()/max(1,self.height())
                for i in self.selected:
                    o=self.objects[i];typ=o.get("type")
                    if typ=="stroke":o["points"]=[[x+dx,y+dy] for x,y in o["points"]]
                    elif typ=="text":o["x"]+=dx;o["y"]+=dy
                    elif typ=="shape":o["a"]=[o["a"][0]+dx,o["a"][1]+dy];o["b"]=[o["b"][0]+dx,o["b"][1]+dy]
                self.update();return
            if self.start is not None:self.lasso=QRectF(self.start,pos).normalized();self.update();return
        if self.current:
            if self.current["type"]=="shape":self.current["b"]=self.norm(pos)
            else:self.current["points"].append(self.norm(pos))
            self.update()
    def _autocorrect(self,o):
        pts=o.get("points",[])
        if len(pts)<4:return
        xs=[p[0] for p in pts];ys=[p[1] for p in pts];w=max(xs)-min(xs);h=max(ys)-min(ys);diag=math.hypot(w,h)
        if diag<.025:return
        poly=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]));end=math.hypot(pts[-1][0]-pts[0][0],pts[-1][1]-pts[0][1])
        if poly>0 and end/poly>.92:
            o.clear();o.update({"type":"shape","shape":"line","a":pts[0],"b":pts[-1],"color":self.color,"width":self.pen_width});return
        if end < diag*.3 and .45 < (w/max(h,.001)) < 2.2:
            o.clear();o.update({"type":"shape","shape":"ellipse","a":[min(xs),min(ys)],"b":[max(xs),max(ys)],"color":self.color,"width":self.pen_width})
    def release(self,pos):
        if self.tool=="lasso":
            if self.moving:self.moving=False;self.move_last=None;self.changed.emit();self.update();return
            if self.lasso is not None:
                self.selected=[i for i,o in enumerate(self.objects) if self.lasso.intersects(self.bbox(o))];self.lasso=None;self.start=None;self.update()
            return
        if self.current:
            if self.current["type"]=="shape":self.current["b"]=self.norm(pos)
            else:
                self.current["points"].append(self.norm(pos))
                if self.current.get("tool")=="autoshape":self._autocorrect(self.current)
            self.current=None;self.changed.emit();self.update()
    def event(self,e):
        t=e.type()
        if t in (QEvent.Type.TouchBegin,QEvent.Type.TouchUpdate,QEvent.Type.TouchEnd,QEvent.Type.TouchCancel):
            pts=e.points() if hasattr(e,"points") else e.touchPoints()
            if len(pts)==1:
                p=pts[0].position()
                if t==QEvent.Type.TouchBegin:self.press(p)
                elif t==QEvent.Type.TouchUpdate:self.move(p)
                elif t==QEvent.Type.TouchEnd:self.release(p)
                e.accept();return True
            if len(pts)>=2:self.current=None;e.accept();return True
        return super().event(e)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:self.press(e.position())
    def mouseMoveEvent(self,e):
        if e.buttons()&Qt.MouseButton.LeftButton:self.move(e.position())
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:self.release(e.position())
    def paint_template(self,p):
        p.fillRect(self.rect(),QColor("#fffefa"));p.setPen(QPen(QColor("#dedbd2"),1))
        if self.template=="lined":
            for y in range(48,self.height(),36):p.drawLine(24,y,self.width()-24,y)
        elif self.template=="grid":
            for x in range(0,self.width(),32):p.drawLine(x,0,x,self.height())
            for y in range(0,self.height(),32):p.drawLine(0,y,self.width(),y)
        elif self.template=="dotted":
            for x in range(18,self.width(),28):
                for y in range(18,self.height(),28):p.drawPoint(x,y)
        elif self.template=="cornell":
            p.drawLine(int(self.width()*.28),30,int(self.width()*.28),self.height()-80);p.drawLine(20,self.height()-80,self.width()-20,self.height()-80);p.drawLine(20,60,self.width()-20,60)
    def _arrow(self,p,a,b):
        p.drawLine(a,b);ang=math.atan2(b.y()-a.y(),b.x()-a.x());l=16
        p1=QPointF(b.x()-l*math.cos(ang-.55),b.y()-l*math.sin(ang-.55));p2=QPointF(b.x()-l*math.cos(ang+.55),b.y()-l*math.sin(ang+.55));p.drawLine(b,p1);p.drawLine(b,p2)
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing,True);self.paint_template(p)
        for o in self.objects:
            typ=o.get("type","stroke")
            if typ=="stroke":
                pts=o.get("points",[])
                if len(pts)<2:continue
                c=QColor(o.get("color","#202020"));
                if o.get("tool")=="highlighter":c.setAlpha(85)
                p.setPen(QPen(c,float(o.get("width",2.6)),Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
                for a,b in zip(pts,pts[1:]):p.drawLine(self.denorm(a),self.denorm(b))
            elif typ=="text":
                p.setPen(QColor(o.get("color","#202020")));f=QFont();f.setPointSize(int(o.get("size",18)));p.setFont(f);p.drawText(QPointF(o["x"]*self.width(),o["y"]*self.height()),o.get("text",""))
            elif typ=="shape":
                p.setPen(QPen(QColor(o.get("color","#202020")),float(o.get("width",2.6)),Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));a=self.denorm(o["a"]);b=self.denorm(o["b"]);r=QRectF(a,b).normalized();shape=o.get("shape")
                if shape=="line":p.drawLine(a,b)
                elif shape=="rectangle":p.drawRect(r)
                elif shape=="ellipse":p.drawEllipse(r)
                elif shape=="triangle":
                    poly=QPolygonF([QPointF(r.center().x(),r.top()),QPointF(r.left(),r.bottom()),QPointF(r.right(),r.bottom()),QPointF(r.center().x(),r.top())]);p.drawPolyline(poly)
                elif shape=="arrow":self._arrow(p,a,b)
        if self.lasso:p.setPen(QPen(QColor("#666"),1,Qt.PenStyle.DashLine));p.drawRect(self.lasso)
        if self.selected:
            p.setPen(QPen(QColor("#555"),1,Qt.PenStyle.DashLine))
            for i in self.selected:p.drawRect(self.bbox(self.objects[i]))
