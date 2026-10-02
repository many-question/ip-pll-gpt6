"""Compare SS internal clock evidence and separately named repair screens."""
from pathlib import Path
import hashlib,json
import numpy as np
from analyze import divider,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'

def load(job):
    rec=json.loads((job/'result.json').read_text())
    assert rec.get('local_outputs_sha256') and rec['remote_inputs_match']
    assert 'spectre completes with 0 errors' in (job/'spectre.out').read_text(errors='replace')
    with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    return rec,d

def signals(d,start,end):
    t=d['time'];s=(t>=start*1e-9)&(t<end*1e-9);tt=t[s];out={}
    for k in ['q1','XD.ci','XD.gn','XD.cb','XD.ck','XD.ckb','XD.run','XD.load','XD.loadb',
              'XD.r0','XD.r1','XD.r2','XD.r3','XD.r4','XD.r5','XD.r6','XD.d6','predata','data']:
        if k not in d:continue
        y=d[k][s];out[k]=dict(min_v=float(min(y)),max_v=float(max(y)),
            fraction_above_0p6v=float(np.trapezoid((y>.6).astype(float),tt)/(tt[-1]-tt[0])),
            rising_edges=len(cross(tt,y)))
    return out

rows=[]
for run in sorted(R.glob('bankdiag*'))+sorted(R.glob('bankclk*')):
    for rp in sorted(run.glob('*/result.json')):
        if not json.loads(rp.read_text()).get('local_outputs_sha256'):continue
        log=(rp.parent/'spectre.out').read_text(errors='replace')
        if 'spectre completes with 0 errors' not in log:
            rows.append(dict(run=run.name,case=rp.parent.name,source_result=rp.relative_to(ROOT).as_posix(),
                simulator_completed=False,errors=[x.strip() for x in log.splitlines() if 'ERROR (' in x]))
            continue
        rec,d=load(rp.parent);t=d['time'];m=int(rp.parent.name.split('_')[1][1:])
        row=dict(run=run.name,case=rp.parent.name,source_result=rp.relative_to(ROOT).as_posix(),
            source_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),inputs_sha256=rec['inputs_sha256'],
            reset_window=signals(d,2,7),steady_window=signals(d,float(t[-1]*1e9-10),float(t[-1]*1e9)),
            scope='MOS divider bank and retimer, ideal20ps RF,1.2V,10fF; not PLL capture/noise.')
        if rp.parent.name.startswith('bankclk'):
            d={k:v[t>=60e-9] for k,v in d.items() if len(v)==len(t)}
            row['divider']=divider(d,m)
            row['divider']['scope']='MOS divider bank plus retimer, ideal20ps RF,1.2V,10fF; final40ns. Not PLL power.'
        rows.append(row)
out=dict(scope=__doc__,rows=rows,
    interpretation='Baseline SS/6 clock amplitude collapses. SS/10 and/14 load correct reset state, then lose the circulating pattern. Separate two-buffer candidate tests clock-path causality; no fullPLL substitution yet.')
(H/'results/ss_clock_repair.json').write_text(json.dumps(out,indent=2)+'\n')
for row in rows:
    print(row['run'],row['case'],row.get('divider',{}).get('passed'),
          {k:[round(v['min_v'],3),round(v['max_v'],3)] for k,v in row.get('steady_window',{}).items() if k in ['XD.ck','XD.ckb','XD.r0']})
