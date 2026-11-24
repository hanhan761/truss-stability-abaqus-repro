"""Independent imperfect B23 specimens; no mechanical coupling between replicas."""
from pathlib import Path
import math,random
from build_decks import deck,MEMBERS

N=16
RODS=(1,4,5)
E=230000.
H=1.5
I=20*H**3/12
def training_input(chord,plate,geom_index,plate_index,reps):
    raw,rods=deck(chord,260,plate,N)
    lines=raw.splitlines()
    node_rows=lines[lines.index('*NODE,NSET=ALL_NODES')+1:lines.index('*ELEMENT,TYPE=B23,ELSET=ALL_BEAMS')]
    pts={int(row.split(',')[0]):tuple(map(float,row.split(',')[1:])) for row in node_rows}
    node_out=[];el_out=[];eq_out=[];bound=[];move=[];gauges=[];rf=[];meta=[]
    for rep in reps:
        off=1000*rep
        rng=random.Random(20261123+geom_index*1000+plate_index*100+rep)
        amp=[(1 if rng.random()>.5 else -1)*rng.uniform(.06,.48) for _ in MEMBERS]
        second=[rng.uniform(-.15,.15) for _ in MEMBERS]
        xy=dict(pts)
        for k,ns in enumerate(rods):
            x0,y0=pts[ns[0]];x1,y1=pts[ns[-1]]
            dx,dy=x1-x0,y1-y0;length=math.hypot(dx,dy)
            for q,label in enumerate(ns[1:-1],1):
                t=q/N
                curve=amp[k]*(math.sin(math.pi*t)+second[k]*math.sin(2*math.pi*t))
                xy[label]=(x0+t*dx-curve*dy/length,y0+t*dy+curve*dx/length)
            for q,(a,b) in enumerate(zip(ns,ns[1:]),1):
                el_out.append(f'{off+k*N+q}, {off+a}, {off+b}')
        for node,(x,y) in sorted(xy.items()):node_out.append(f'{off+node}, {x+700*rep:.12f}, {y:.12f}')
        for ix,line in enumerate(lines):
            if line!='*EQUATION':continue
            a,d,wa,b,e,wb=lines[ix+2].split(',')
            eq_out.extend(('*EQUATION','2',f'{off+int(a)}, {d}, {wa}, {off+int(b)}, {e}, {wb}'))
        bound.extend((f'{off+1},1,2',f'{off+5},2,2'))
        move.append(f'{off+3},2,2,-0.9')
        rf.extend(off+k for k in [1,3,5])
        ids=[[off+(rod-1)*N+N//2,off+(rod-1)*N+N//2+1] for rod in RODS]
        gauges.extend(x for pair in ids for x in pair)
        meta.append(dict(id=f'C{chord}_{plate}_r{rep:02}',chord=chord,plate=plate,rep=rep,
                         imperfection_mm=amp,second_harmonic_ratio=second,off=off,gauges=ids))
    def ids(seq):return [', '.join(map(str,seq[k:k+12])) for k in range(0,len(seq),12)]
    section=lines.index('*BEAM GENERAL SECTION,SECTION=GENERAL,ELSET=ALL_BEAMS')
    inp=['*HEADING',f'{len(reps)} independent imperfect specimens, L5 {chord}, {plate}',
         '*NODE',*node_out,'*ELEMENT,TYPE=B23,ELSET=ALL_BEAMS',*el_out,*lines[section:section+4],
         '*ELSET,ELSET=GAUGES',*ids(gauges),'*NSET,NSET=PROBES',*ids(rf),*eq_out,
         '*BOUNDARY',*bound,'*AMPLITUDE,NAME=TRAVEL',
         '0.,0., 0.28,0.012, 0.50,0.055, 0.70,0.20','1.,1.',
         '*STEP,NAME=LOAD,NLGEOM=YES,INC=2500','*STATIC','0.008,1.,1.E-9,0.016',
         '*BOUNDARY,AMPLITUDE=TRAVEL',*move,'*OUTPUT,FIELD,NUMBER INTERVAL=64,TIME MARKS=YES',
         '*NODE OUTPUT,NSET=PROBES','U,RF','*ELEMENT OUTPUT,ELSET=GAUGES','SF,SE','*END STEP']
    return '\n'.join(inp)+'\n',meta
