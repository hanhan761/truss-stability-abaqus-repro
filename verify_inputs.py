import math
def inspect_inputs(text, cases):
    nodes={};elements={};eq=[];bcs=[];act=[];gauges=[];prestep=True
    for line in text.splitlines():
        if line.startswith('*'):
            kw=line.split(',')[0].upper()
            if kw=='*STEP':prestep=False
            continue
        v=[x.strip() for x in line.split(',')]
        if kw=='*NODE':nodes[int(v[0])]=tuple(map(float,v[1:]))
        if kw=='*ELEMENT':elements[int(v[0])]=tuple(map(int,v[1:]))
        if kw=='*EQUATION' and len(v)==6:eq.append(v)
        if kw=='*BOUNDARY':(bcs if prestep else act).append(v)
        if kw=='*ELSET':gauges.extend(map(int,v))
    assert len(elements)==112*len(cases)
    assert set(gauges)=={i for c in cases for pair in c['gauges'] for i in pair}
    for k,(a,b) in elements.items():assert k//1000==a//1000==b//1000 and a in nodes and b in nodes
    for a,d,wa,b,e,wb in eq:
        assert int(a)//1000==int(b)//1000 and d==e and d in ('1','2') and (float(wa),float(wb))==(1.,-1.)
        assert math.dist(nodes[int(a)],nodes[int(b)])<1e-8
    assert {(int(a),int(i),int(j)) for a,i,j in bcs}=={(c['off']+n,i,j) for c in cases for n,i,j in [(1,1,2),(5,2,2)]}
    assert {(int(a),int(i),int(j),float(h)) for a,i,j,h in act}=={(c['off']+3,2,2,-.9) for c in cases}
    for c in cases:
        off=c['off']
        def ends(i):return elements[off+(i-1)*16+1][0],elements[off+i*16][1]
        for side,ns in [('left',[ends(1)[1],ends(2)[0],ends(5)[0]]),('right',[ends(3)[1],ends(4)[0],ends(5)[1]])]:
            assert len(set(ns))==(1 if c['plate'] in (side,'both') else 3)
        assert abs(math.dist(nodes[off+2],nodes[off+4])-c['chord'])<1e-7
