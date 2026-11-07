from pathlib import Path
import csv, math
from lxml import etree
from svgpathtools import parse_path

ROOT=Path('/home/ubuntu/garment_pattern_preview/wedding_gown_open_source')
SVG=ROOT/'open_source_exports/M/M_pattern.svg'
CSV=ROOT/'data/pattern_piece_dimensions.csv'
OUT=Path('/home/ubuntu/garment_pattern_preview/seamly_native_gown')
OUT.mkdir(parents=True,exist_ok=True)

rows=[]
with CSV.open(encoding='utf-8-sig',newline='') as f:
    rows=[r for r in csv.DictReader(f) if r['size']=='M']
svg=etree.parse(str(SVG)); ns={'s':'http://www.w3.org/2000/svg'}
paths=svg.xpath('//s:path',namespaces=ns)
if len(rows)!=len(paths): raise SystemExit(f'piece mapping mismatch: {len(rows)} rows, {len(paths)} paths')
# Seamly stores native project coordinates in mm; source GarmentCode SVG is in cm.
mm=10.0
root=etree.Element('pattern')
for tag,text in [('version','0.6.8'),('unit','mm'),('description','Image-estimated bridal gown M size; source contours from GarmentCode; exported by Seamly2D native CAD'),('notes','Prototype estimate only. No lining pattern or verified seam-pair notches are present.'),('gradation',None),('patternLabel',None),('measurements','../measurements/multisize/gost_man_ru.smms'),('increments',None)]:
    e=etree.SubElement(root,tag)
    if tag=='gradation':
        # Valid defaults from the linked GOST multisize measurements; geometry remains direct M-size contours.
        e.set('custom','true'); e.set('defHeight','1640'); e.set('defSize','520')
        etree.SubElement(e,'heights',all='true'); etree.SubElement(e,'sizes',all='true')
    elif tag=='increments':
        # Seamly pattern requires a valid increments block; the pieces are direct contour geometry.
        pass
    elif text is not None: e.text=text
block=etree.SubElement(root,'draftBlock',name='婚纱礼服_M_图片估算')
calc=etree.SubElement(block,'calculation')
model=etree.SubElement(block,'modeling')
pieces=etree.SubElement(block,'pieces')
next_id=10000
cursor_x=40.0
cursor_y=40.0
row_height=0.0
row_width=2400.0
summary=[]
for idx,(row,elem) in enumerate(zip(rows,paths),1):
    path=parse_path(elem.get('d'))
    # Sample curved SVG edges at roughly 8 mm intervals; retain all line endpoints.
    pts=[]
    for seg in path:
        length=seg.length(error=1e-3)*mm
        n=max(1,min(300,math.ceil(length/8.0)))
        for k in range(n):
            z=seg.point(k/n)
            xy=(round(z.real*mm,4),round(z.imag*mm,4))
            if not pts or math.dist(xy,pts[-1])>0.03: pts.append(xy)
    # closed outlines don't need duplicate endpoint; the CAD closes the final node to first.
    if len(pts)>1 and math.dist(pts[0],pts[-1])<0.05: pts.pop()
    if len(pts)<3: raise SystemExit(f'{row["piece_code"]} has fewer than 3 points')
    # Place pieces in CAD model space so details do not overlap on the exported sheet.
    xmin=min(p[0] for p in pts); ymin=min(p[1] for p in pts)
    xmax=max(p[0] for p in pts); ymax=max(p[1] for p in pts)
    piece_w=xmax-xmin; piece_h=ymax-ymin
    if cursor_x + piece_w + 40 > row_width:
        cursor_x=40.0
        cursor_y+=row_height+100.0
        row_height=0.0
    pts=[(round(x-xmin+cursor_x,4),round(y-ymin+cursor_y,4)) for x,y in pts]
    label_x=cursor_x+piece_w/2
    label_y=cursor_y+piece_h/2
    row_height=max(row_height,piece_h)
    coords=[]; model_ids=[]
    for j,(x,y) in enumerate(pts):
        oid=next_id; mid=next_id+1; next_id+=2
        name=f'{row["piece_code"]}_{j+1}'
        etree.SubElement(calc,'point',id=str(oid),mx='0',my='0',name=name,type='single',x=str(x),y=str(y))
        etree.SubElement(model,'point',id=str(mid),idObject=str(oid),inUse='true',mx='0',my='0',type='modeling')
        coords.append((x,y)); model_ids.append(mid)
    piece_id=next_id; next_id+=1
    piece=etree.SubElement(pieces,'piece',closed='1',id=str(piece_id),mx='0',my='0',name=row['piece_name_cn'],seamAllowance='0',version='2',width='0')
    # Data is an in-CAD pattern-information label. The outer cloth only exists in source engine.
    center_id=next_id; next_id+=1
    etree.SubElement(calc,'point',id=str(center_id),mx='0',my='0',name=f'{row["piece_code"]}_LABEL_CENTER',type='single',x=str(round(label_x,4)),y=str(round(label_y,4)))
    data_label=etree.SubElement(piece,'data',annotation='M码｜面布｜图片估算版',centerAnchor=str(center_id),foldPosition='',fontSize='14',height='48',letter='',mx='0',my='0',onFold='false',orientation='',quantity='1',rotation='',rotationWay='',tilt='',visible='true',width='120')
    for text,bold,inc in [('%pName%','true','1'),('%pAnnotation%','false','0'),('数量 %pQuantity%','false','0')]:
        etree.SubElement(data_label,'line',alignment='4',bold=bold,italic='false',sfIncrement=inc,text=text)
    etree.SubElement(piece,'patternInfo',fontSize='0',height='',mx='0',my='0',rotation='',visible='false',width='')
    # Grainline is CAD-native line mark oriented along the geometrical long axis (estimate only).
    bx=max(x for x,y in coords)-min(x for x,y in coords); by=max(y for x,y in coords)-min(y for x,y in coords)
    angle='0' if bx>=by else '90'
    gl_len=round(max(10,max(bx,by)*0.72),2)
    grain_top=next_id; grain_bottom=next_id+1; next_id+=2
    if angle=='0':
        gx1,gy1=label_x+gl_len/2,label_y; gx2,gy2=label_x-gl_len/2,label_y
    else:
        gx1,gy1=label_x,label_y-gl_len/2; gx2,gy2=label_x,label_y+gl_len/2
    etree.SubElement(calc,'point',id=str(grain_top),mx='0',my='0',name=f'{row["piece_code"]}_GRAIN_TOP',type='single',x=str(round(gx1,4)),y=str(round(gy1,4)))
    etree.SubElement(calc,'point',id=str(grain_bottom),mx='0',my='0',name=f'{row["piece_code"]}_GRAIN_BOTTOM',type='single',x=str(round(gx2,4)),y=str(round(gy2,4)))
    etree.SubElement(piece,'grainline',arrows='2',length=str(gl_len),mx='0',my='0',rotation=angle,topAnchor=str(grain_top),bottomAnchor=str(grain_bottom),visible='true')
    nodes=etree.SubElement(piece,'nodes')
    for mid in model_ids:
        etree.SubElement(nodes,'node',idObject=str(mid),type='NodePoint')
    summary.append((row['piece_code'],row['piece_name_cn'],len(coords),round(bx/10,2),round(by/10,2),angle,gl_len))
    cursor_x+=piece_w+100.0

outxml=OUT/'婚纱礼服_M_Seamly2D.sm2d'
etree.ElementTree(root).write(str(outxml),encoding='UTF-8',xml_declaration=True,pretty_print=True)
with (OUT/'native_piece_map.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['裁片代码','CAD中文名称','轮廓采样点数','宽cm','高cm','CAD纱向角度估算','纱向标记长mm'])
    w.writerows(summary)
print('project',outxml,'pieces',len(summary),'points',sum(x[2] for x in summary))
