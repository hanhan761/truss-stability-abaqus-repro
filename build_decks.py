"""Independent planar truss Abaqus/Standard input generator (N, mm, MPa)."""
import json
import math
from pathlib import Path

MEMBERS = [(0,1),(1,2),(2,3),(3,4),(1,3),(0,2),(2,4)]
PLATES = {'none':set(), 'left':{1}, 'right':{3}, 'both':{1,3}}
GEOMETRIES = [(215,260),(260,260),(305,260),(240,280),(335,270)]

def deck(chord, other, plate, n):
    # The outside triangles are equilateral and face outward.
    angle = math.acos(chord / (2 * other))
    def along(theta):
        return other * math.cos(theta), other * math.sin(theta)
    far_x, far_y = along(angle - math.pi/3)
    near_x, near_y = along(angle)
    joints = [(-far_x,far_y),(-near_x,near_y),(0.,0.),(near_x,near_y),(far_x,far_y)]
    points, elements, equations = list(joints), [], []
    primary = set()
    rod_nodes = []
    for j,k in MEMBERS:
        ids = []
        for step in range(n+1):
            end = j if step == 0 else k if step == n else None
            if end is not None and (end not in primary or end in PLATES[plate]):
                ids.append(end+1)
                primary.add(end)
                continue
            pos = step/n
            points.append(tuple(a+(b-a)*pos for a,b in zip(joints[j],joints[k])))
            ids.append(len(points))
            if end is not None:
                for dof in (1,2):
                    equations += ['*EQUATION','2',f'{ids[-1]}, {dof}, 1., {end+1}, {dof}, -1.']
        rod_nodes.append(ids)
        elements.extend(zip(ids,ids[1:]))
    A = 20*1.5
    I11, I22 = 20*1.5**3/12, 1.5*20**3/12
    E, nu = 230000, 0.288
    jtorsion = 20*1.5**3/3*(1-0.63*1.5/20)
    lines = ['*HEADING',f'Stability: L5={chord}, Lother={other}, {plate}; {n} B23/rod',
             '*NODE,NSET=ALL_NODES']
    lines.extend(f'{i}, {x:.12f}, {y:.12f}' for i,(x,y) in enumerate(points,1))
    lines.append('*ELEMENT,TYPE=B23,ELSET=ALL_BEAMS')
    lines.extend(f'{i}, {a}, {b}' for i,(a,b) in enumerate(elements,1))
    for i,nodes in enumerate(rod_nodes,1):
        lines.extend([f'*NSET,NSET=ROD_{i}', ', '.join(map(str,nodes))] if len(nodes) <= 16 else
                     [f'*NSET,NSET=ROD_{i}', *[', '.join(map(str,nodes[k:k+16])) for k in range(0,len(nodes),16)]])
    lines.extend(['*BEAM GENERAL SECTION,SECTION=GENERAL,ELSET=ALL_BEAMS',
                  f'{A}, {I11}, 0., {I22}, {jtorsion}', '0.,0.,-1.', f'{E}, {E/(2*(1+nu))}',
                  *equations,'*BOUNDARY','1, 1, 2','5, 2, 2',
                  '*STEP,NAME=UNIT_LOAD,PERTURBATION','*STATIC',
                  '*CLOAD','3, 2, -1.', '*OUTPUT,FIELD','*NODE OUTPUT','U, RF',
                  '*END STEP','*STEP,NAME=BUCKLING,PERTURBATION',
                  '*BUCKLE,EIGENSOLVER=LANCZOS','12,0.', '*CLOAD','3, 2, -1.',
                  '*OUTPUT,FIELD','*NODE OUTPUT','U','*END STEP'])
    return '\n'.join(lines)+'\n', rod_nodes
