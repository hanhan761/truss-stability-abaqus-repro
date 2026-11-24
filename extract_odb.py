"""Check a completed Abaqus job and write its report quantities as JSON."""
import argparse
import hashlib
import json
from pathlib import Path

from odb_readers import read_buckling, read_curves
from prepare import manifest,materialize

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('name',help='job name in cases.json')
    cli.add_argument('--work',type=Path,default=Path('.'),help='folder containing .inp, .odb and .sta')
    cli.add_argument('--out',type=Path,help='if not set, print JSON to stdout')
    args=cli.parse_args()
    spec=manifest(); case=next((c for c in spec['jobs'] if c['name']==args.name),None)
    if not case:cli.error('Unknown case')
    stem=args.work/args.name
    if hashlib.sha256(stem.with_suffix('.inp').read_bytes()).hexdigest()!=case['sha256']:
        raise ValueError('The solved .inp does not match the selected case')
    status=stem.with_suffix('.sta').read_text(errors='replace')
    if 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' not in status:
        raise ValueError('Expected successful Abaqus job status')
    _,meta=materialize(case,spec['design'])
    odb=stem.with_suffix('.odb')
    if case['suite']=='buckling':
        res=read_buckling(odb,meta)
        if max(map(abs,res['balance']))>1e-5 or abs(res['moment'])>1e-3:
            raise ValueError('Failed static unit-load balance')
        res['reference_load_N']=case['reference_load_N']
        res['reference_leading_rods']=case['reference_leading_rods']
        res['difference_from_reference_N']=res['load']-case['reference_load_N']
    else:
        records=read_curves(odb,meta)
        for entry in records:
            if len(entry['rows'])!=65:
                raise ValueError('Expected 65 unthinned frames per specimen')
            entry['stop_frame']=next((i for i,r in enumerate(entry['rows']) if max(map(abs,r[1:4]))>=1200),None)
        res=dict(columns=['F_N','rod1_ue','rod4_ue','rod5_ue','down_mm'],records=records)
    result=json.dumps(dict(name=args.name,inp_sha256=case['sha256'],**res),indent=2,allow_nan=False)+'\n'
    if args.out:
        with args.out.open('x',encoding='utf-8') as f:f.write(result)
    else:print(result,end='')
if __name__=='__main__':main()
