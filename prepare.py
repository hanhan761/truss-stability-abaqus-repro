"""Regenerate original ASCII Abaqus decks; check the archived SHA-256 for each job."""
import argparse
import hashlib
import json
from pathlib import Path

import curve_deck
from build_decks import deck
from tight_controls import tighten
from verify_inputs import inspect_inputs

MANIFEST=Path(__file__).with_name('cases.json')
def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))

def materialize(case, design):
    chord,plate,mesh=case['chord'],case['plate'],case['mesh']
    if case['suite']=='buckling':
        text,rod_nodes=deck(chord,design['other'],plate,mesh)
        metadata=dict(mesh=mesh,rod_nodes=rod_nodes)
    else:
        old_mesh=curve_deck.N
        try:
            curve_deck.N=mesh
            text,metadata=curve_deck.training_input(chord,plate,design['lengths'].index(chord),
                design['plates'].index(plate),case['variants'])
        finally:
            curve_deck.N=old_mesh
        if case['controls']=='tight':
            text=tighten(text)
        if mesh==16:
            inspect_inputs(text,metadata)
    raw=text.encode('ascii')
    if hashlib.sha256(raw).hexdigest()!=case['sha256']:
        raise ValueError('Archived input checksum differs: '+case['name'])
    return raw,metadata

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--suite',choices=['all','buckling','curves','refined'],default='all')
    cli.add_argument('--case',action='append',default=[],help='repeat to select specific job names')
    cli.add_argument('--out',type=Path,help='directory for generated input decks')
    args=cli.parse_args()
    spec=manifest()
    selected=[c for c in spec['jobs'] if (not args.case or c['name'] in args.case)
              and args.suite in ('all',c['suite'])]
    if not selected or (args.case and {c['name'] for c in selected}!=set(args.case)):
        cli.error('Unknown case or incompatible suite')
    for case in selected:
        raw,_=materialize(case,spec['design'])
        if args.out:
            args.out.mkdir(parents=True,exist_ok=True)
            dest=args.out/(case['name']+'.inp')
            if dest.exists() and dest.read_bytes()!=raw:
                cli.error(f'Refusing to overwrite a different file: {dest}')
            if not dest.exists():dest.write_bytes(raw)
    print(f'Checked {len(selected)} input SHA-256 values')
if __name__=='__main__':main()
