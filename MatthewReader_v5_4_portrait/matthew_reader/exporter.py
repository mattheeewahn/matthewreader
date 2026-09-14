from pathlib import Path
import math, shutil
import pymupdf as fitz
from .storage import EXPORT_DIR, ensure_dirs, load_note, load_annotations

COLORS={"yellow":(1.0,.88,.18),"green":(.45,.82,.40),"blue":(.28,.64,1.0),"pink":(1.0,.36,.62)}

def hexrgb(s):
    s=(s or "#202020").lstrip("#")
    try:return tuple(int(s[i:i+2],16)/255 for i in (0,2,4))
    except Exception:return (.12,.12,.12)

def unique_path(folder:Path,name:str):
    folder.mkdir(parents=True,exist_ok=True); p=folder/name
    if not p.exists():return p
    stem,suf=Path(name).stem,Path(name).suffix;i=1
    while True:
        c=folder/f"{stem} ({i}){suf}"
        if not c.exists():return c
        i+=1

def draw_template(page,template,w,h):
    c=(.84,.83,.79)
    if template=="lined":
        y=48
        while y<h-20:page.draw_line((24,y),(w-24,y),color=c,width=.6);y+=36
    elif template=="grid":
        for x in range(0,int(w),32):page.draw_line((x,0),(x,h),color=c,width=.4)
        for y in range(0,int(h),32):page.draw_line((0,y),(w,y),color=c,width=.4)
    elif template=="dotted":
        for x in range(18,int(w),28):
            for y in range(18,int(h),28):page.draw_circle((x,y),.8,color=c,fill=c)
    elif template=="cornell":
        page.draw_line((w*.28,30),(w*.28,h-80),color=c,width=.7);page.draw_line((20,h-80),(w-20,h-80),color=c,width=.7);page.draw_line((20,60),(w-20,60),color=c,width=.7)

def draw_arrow(page,a,b,color,width):
    page.draw_line(a,b,color=color,width=width)
    dx,dy=b.x-a.x,b.y-a.y;ang=math.atan2(dy,dx);l=max(10,width*5)
    p1=fitz.Point(b.x-l*math.cos(ang-.55),b.y-l*math.sin(ang-.55));p2=fitz.Point(b.x-l*math.cos(ang+.55),b.y-l*math.sin(ang+.55))
    page.draw_line(b,p1,color=color,width=width);page.draw_line(b,p2,color=color,width=width)

def render_objects(page,objects,w,h):
    for o in objects:
        typ=o.get("type","stroke");col=hexrgb(o.get("color"));width=float(o.get("width",2.6))
        if typ=="stroke":
            pts=[fitz.Point(x*w,y*h) for x,y in o.get("points",[])]
            opacity=.3 if o.get("tool")=="highlighter" else 1.0
            for a,b in zip(pts,pts[1:]):page.draw_line(a,b,color=col,width=width,stroke_opacity=opacity)
        elif typ=="text":
            page.insert_text((o.get("x",0)*w,o.get("y",0)*h),o.get("text",""),fontsize=float(o.get("size",18)),color=col)
        elif typ=="shape":
            a=fitz.Point(o["a"][0]*w,o["a"][1]*h);b=fitz.Point(o["b"][0]*w,o["b"][1]*h);r=fitz.Rect(a,b);shape=o.get("shape")
            if shape=="line":page.draw_line(a,b,color=col,width=width)
            elif shape=="rectangle":page.draw_rect(r,color=col,width=width)
            elif shape=="ellipse":page.draw_oval(r,color=col,width=width)
            elif shape=="triangle":
                p1=fitz.Point((a.x+b.x)/2,min(a.y,b.y));p2=fitz.Point(min(a.x,b.x),max(a.y,b.y));p3=fitz.Point(max(a.x,b.x),max(a.y,b.y))
                page.draw_polyline([p1,p2,p3,p1],color=col,width=width)
            elif shape=="arrow":draw_arrow(page,a,b,col,width)

def export_note(note_path:Path,destination:Path|None=None):
    ensure_dirs();m,pages=load_note(note_path);dest=destination or unique_path(EXPORT_DIR,f"{m.get('title',Path(note_path).stem)}.pdf")
    doc=fitz.open();w,h=612,792;template=m.get("template","blank")
    for objs in pages:
        pg=doc.new_page(width=w,height=h);draw_template(pg,template,w,h);render_objects(pg,objs,w,h)
    doc.save(str(dest),garbage=4,deflate=True);doc.close();return dest

def export_annotated_pdf(pdf_path:Path,destination:Path|None=None):
    ensure_dirs();dest=destination or unique_path(EXPORT_DIR,f"{Path(pdf_path).stem} - Annotated.pdf")
    doc=fitz.open(str(pdf_path));anno=load_annotations(pdf_path)
    for key,data in anno.get("pages",{}).items():
        try:i=int(key)
        except Exception:continue
        if i<0 or i>=len(doc):continue
        pg=doc[i];r=pg.rect;w,h=r.width,r.height
        for hl in data.get("highlights",[]):
            x1,y1,x2,y2=hl.get("rect",[0,0,0,0]);rr=fitz.Rect(x1*w,y1*h,x2*w,y2*h);c=COLORS.get(hl.get("color"),COLORS["yellow"])
            pg.draw_rect(rr,color=None,fill=c,fill_opacity=.28,overlay=True)
        for s in data.get("strokes",[]):
            pts=[fitz.Point(x*w,y*h) for x,y in s.get("points",[])];c=hexrgb(s.get("color"));wd=float(s.get("width",2.5))
            for a,b in zip(pts,pts[1:]):pg.draw_line(a,b,color=c,width=wd,overlay=True)
    doc.save(str(dest),garbage=4,deflate=True);doc.close();return dest

def copy_export_to_usb(src:Path,mount:Path):
    dest=unique_path(Path(mount),Path(src).name);shutil.copy2(src,dest);return dest
