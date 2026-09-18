"""Bounded per-channel coarse-code search using two actual-loaded fine endpoints.

Every attempt runs as its own immutable Spectre job. This is a testbench search,
not the on-chip FLL or evidence that the complete PLL has captured.
"""
import argparse,subprocess,sys
from build_channel_tb import channel,H
from analyze import R,measure,endpoint_windows
import json,math
import numpy as np

def first_code(f):
    return round(8+(1/f**2-1/(3.947e9)**2)*230/(1/(2.715e9)**2-1/(3.947e9)**2))

def prior_code(corner,k,freq,r2=False):
    rows=[]
    for p in (H/'results').glob('*_search.json'):
        try:rows.extend(json.loads(p.read_text()))
        except json.JSONDecodeError:continue # another batch may be publishing a record
    all_same=[x for x in rows if (x.get('revision','r1')=='r2')==r2]
    same=[x for x in all_same if x['k']==k]
    own=[x for x in same if x.get('corner')==corner]
    if own:
        x=max(own,key=lambda x:x['margin_hz'])
        if x['margin_hz']>600e3:return x['code']
    # All hints below are derived from measurements. They only choose the next
    # experiment; every accepted point still needs its own loaded simulation.
    target_m=14 if k==9 else 12 if k<=11 else 10 if k<=13 else 8 if k<=18 else 6 if k<=27 else 4
    weight={4:4,6:4.5,8:6,10:5,12:6,14:7}
    accepted_own=[x for x in all_same if x.get('corner')==corner and x.get('pass_check')]
    equal=[x for x in accepted_own if x['fvco_hz']==freq]
    if equal:
        x=min(equal,key=lambda x:abs(weight[x['m']]-weight[target_m]))
        return round(x['code']+.75*(weight[x['m']]-weight[target_m]))
    if len(accepted_own)>=3:
        samples=sorted((1/((x['low']['f_ghz']+x['high']['f_ghz'])/2)**2,
                        x['code']+.75*(weight[x['m']]-weight[target_m])) for x in accepted_own)
        t=1/(freq/1e9)**2
        if samples[0][0]<=t<=samples[-1][0]:
            return round(float(np.interp(t,[x[0] for x in samples],[x[1] for x in samples])))
    accepted=[x for x in same if x.get('pass_check')]
    if accepted:return max(accepted,key=lambda x:x['margin_hz'])['code']
    if r2:
        older=[x for x in rows if x.get('corner')==corner and x.get('revision','r1')=='r1' and x['k']==k]
        offsets=[]
        for x in accepted_own:
            prev=[v for v in rows if v.get('revision','r1')=='r1' and v['corner']==corner and v['k']==x['k']]
            if prev:
                old=max(prev,key=lambda v:v['margin_hz']);offsets.append((abs(x['fvco_hz']-freq),x['code']-old['code']))
        delta=round(float(np.median([x[1] for x in sorted(offsets)[:3]]))) if offsets else -round(2+2*(4e9-freq)/(4e9-2.688e9))
        if older:return max(older,key=lambda x:x['margin_hz'])['code']+delta
        return first_code(freq)+delta
    return first_code(freq)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--corner',choices=['tt','ss','ff'],required=True)
    ap.add_argument('--ks',type=int,nargs='*');ap.add_argument('--tag',default='channel');ap.add_argument('--settled',action='store_true')
    ap.add_argument('--r2',action='store_true');ap.add_argument('--guard-mhz',type=float,default=.6)
    args=ap.parse_args();corner=args.corner
    targets=json.loads((H/'results/required_channels.json').read_text())
    if args.ks:targets=[x for x in targets if x['k'] in args.ks]
    history=H/'results'/f'{args.tag}_{corner}_search.json'
    records=json.loads(history.read_text()) if history.exists() else []
    for target in targets:
        k=target['k'];m=target['m'];freq=target['fvco_hz'];code=max(0,min(255,prior_code(corner,k,freq,args.r2)))
        tried={};accepted=None
        for attempt in range(5):
            name=f'{args.tag}_{corner}_k{k}_c{code}';run=f'{args.tag}_{corner}_k{k}_c{code}'
            p=R/run/name
            if not (p/'result.json').exists():
                channel(name,code,m,corner,step=2e-12,settled=args.settled,**(dict(fixed=10e-15,fine=4.5e-6) if args.r2 else {}))
                cmd=[sys.executable,str(H/'run_spectre.py'),'--run-id',run,'--mode','ax','--threads','2',
                     '--preset-override','maxstep','--cases',name]
                status=subprocess.run(cmd).returncode
                if status:raise RuntimeError(f'Simulation failed: {name}, see retained job')
            windows=endpoint_windows((p/'inputs'/f'{name}.scs').read_text());lo=measure(p,windows[0]);hi=measure(p,windows[1])
            a,b=lo['f_ghz']*1e9,hi['f_ghz']*1e9;center=(a+b)/2
            margin=min(freq-min(a,b),max(a,b)-freq)
            valid=lo['divide_valid'] and hi['divide_valid']
            row=dict(**target,corner=corner,case=name,run=run,code=code,low=lo,high=hi,revision='r2' if args.r2 else 'r1',
                     margin_hz=margin,numeric_guard_hz=args.guard_mhz*1e6,pass_check=bool(margin>args.guard_mhz*1e6 and valid))
            tried[code]=row;records=[x for x in records if x['case']!=name]+[row]
            print('CHANNEL',corner,k,code,round(a/1e6,3),round(b/1e6,3),'target',freq/1e6,'valid',valid,'margin_MHz',round(margin/1e6,3),flush=True)
            (H/'results'/f'{args.tag}_{corner}_search.json').write_text(json.dumps(records,indent=2)+'\n')
            if row['pass_check']:accepted=row;break
            if not valid and margin>0:
                print('PHYSICAL_FAIL',name,flush=True);break
            slope=12e6*(center/4e9)**3
            if len(tried)>1:
                other=next((v for c,v in reversed(list(tried.items())) if c!=code),None)
                measured=((other['low']['f_ghz']+other['high']['f_ghz'])*.5e9-center)/(code-other['code'])
                if measured>0:slope=measured
            estimate=max(0,min(255,round(code+(center-freq)/slope)))
            candidates=sorted((c for c in range(max(0,estimate-3),min(255,estimate+3)+1) if c not in tried),key=lambda c:abs(c-(code+(center-freq)/slope)))
            if not candidates:break
            code=candidates[0]
        if not accepted:
            print('UNRESOLVED',corner,k,flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
