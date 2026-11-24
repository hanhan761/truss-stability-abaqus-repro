"""Read the ODB using Abaqus Python. These routines match the archived analyses."""
import math
import re
from odbAccess import openOdb
from curve_deck import E,H,I

VALUE = re.compile(r'eigenvalue\s*=\s*([-+.0-9EeDd]+)', re.IGNORECASE)

def read_buckling(path, case):
    odb = openOdb(path=str(path), readOnly=True)
    try:
        props = {n.label:tuple(map(float,n.coordinates)) for instance in odb.rootAssembly.instances.values() for n in instance.nodes}
        static = odb.steps['UNIT_LOAD'].frames[-1]
        rf = {u.nodeLabel:tuple(map(float,u.data)) for u in static.fieldOutputs['RF'].values if u.nodeLabel in (1,5)}
        reactions = [rf[1],rf[5]]
        balance = [reactions[0][0]+reactions[1][0],reactions[0][1]+reactions[1][1]-1.]
        moment = props[1][0]*reactions[0][1]-props[1][1]*reactions[0][0]+props[5][0]*reactions[1][1]-props[5][1]*reactions[1][0]
        modes = []
        for frame in odb.steps['BUCKLING'].frames:
            match = VALUE.search(frame.description)
            if not match:
                continue
            value = float(match.group(1).replace('D','E').replace('d','e'))
            if value <= 0:
                continue
            displacements = {u.nodeLabel:tuple(map(float,u.data)) for u in frame.fieldOutputs['U'].values}
            bending = []
            for nodes in case['rod_nodes']:
                dx = props[nodes[-1]][0]-props[nodes[0]][0]
                dy = props[nodes[-1]][1]-props[nodes[0]][1]
                length = math.hypot(dx,dy)
                w = [(-dy*displacements[i][0]+dx*displacements[i][1])/length for i in nodes]
                energy = sum((a-2*b+c)**2 for a,b,c in zip(w,w[1:],w[2:])) / (length/case['mesh'])**3
                bending.append(energy)
            modes.append(dict(load=value,mode=int(frame.mode),bending=bending))
        modes.sort(key=lambda m:m['load'])
        if not modes:
            raise ValueError('No positive eigenload found in the ODB')
        leader_set = set()
        for m in modes:
            if m['load']>modes[0]['load']*1.0005:
                break
            leader_set.update(i for i,val in enumerate(m['bending'],1) if val>=0.98*max(m['bending']))
        return dict(load=modes[0]['load'], modes=modes[:5], lead=sorted(leader_set),
                    reactions=reactions,balance=balance,moment=moment)
    finally:
        odb.close()

def component(field,code):
    labels=list(field.componentLabels)
    if labels and code not in labels:raise ValueError((field.name,labels,code))
    index=labels.index(code) if labels else 0
    vals={}
    for v in field.values:
        data=v.data
        val=float(data[index]) if hasattr(data,'__len__') else float(data)
        vals.setdefault(v.elementLabel,[]).append(val)
    return {k:sum(v)/len(v) for k,v in vals.items()}
def read_curves(path,cases):
    odb=openOdb(path=str(path),readOnly=True)
    try:
        frames=odb.steps['LOAD'].frames
        if len(frames)<60 or abs(frames[-1].frameValue-1.)>1e-6:raise ValueError('incomplete loading schedule')
        records=[dict(**c,rows=[],max_force_residual_N=0.,max_moment_curvature_diff_ue=0.) for c in cases]
        for frame in frames:
            f=frame.fieldOutputs
            rf={v.nodeLabel:float(v.data[1]) for v in f['RF'].values}
            u={v.nodeLabel:float(v.data[1]) for v in f['U'].values}
            moments=component(f['SM'],'SM1')
            curv=component(f['SK'],'SK1')
            for r in records:
                off=r['off'];force=-rf[off+3];stroke=-u[off+3]
                r['max_force_residual_N']=max(r['max_force_residual_N'],abs(rf[off+1]+rf[off+5]-force))
                strain=[]
                for a,b in r['gauges']:
                    eps=.5*(curv[a]+curv[b])*H*1e6
                    moment_eps=.5*(moments[a]+moments[b])*H/(E*I)*1e6
                    r['max_moment_curvature_diff_ue']=max(r['max_moment_curvature_diff_ue'],abs(eps-moment_eps))
                    strain.append(eps)
                r['rows'].append([force,*strain,stroke])
        for r in records:
            if not all(math.isfinite(x) for row in r['rows'] for x in row):raise ValueError('nonfinite')
            if max(abs(x) for x in r['rows'][0])>1e-5 or abs(r['rows'][-1][-1]-.9)>1e-5:raise ValueError('stroke/zero')
            if r['max_force_residual_N']>.12 or r['max_moment_curvature_diff_ue']>1.0:raise ValueError(('balance or curvature',r['id'],r['max_force_residual_N'],r['max_moment_curvature_diff_ue']))
        return records
    finally:odb.close()
