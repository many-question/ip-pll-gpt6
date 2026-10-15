"""Review the bounded K41 recheck candidate; accepts a new output path only."""
from pathlib import Path
import json,sys
import numpy as np
from analyze_rt4_fast_range import analyze,H,R,ROOT,sha

def main():
    out=Path(sys.argv[1]);assert not out.exists()
    pp=H/'results/rt4_recenter109_protocol.json';p=json.loads(pp.read_text());c=p['cases'][0]
    row=analyze(c,p)
    if row['state']=='completed':
        row['interpretation']='Pass' if row['fast_functional_screen_passed'] else 'No valid capture by120us; inspect fresh-count sequence and any supervisor restart.'
        wave=R/c['run']/c['case']/'waveforms.npz'
        with np.load(wave) as z:d={k:z[k] for k in z.files if k!='units'}
        t=d['time'];assert len(t)==60001 and np.all(np.diff(t)>0)
        assert all(np.all(np.isfinite(v)) for v in d.values())
        bits=lambda pref,n:sum((d[pref+str(i)]>.6).astype(int)*(1<<i) for i in range(n))
        st=bits('XP.XC.state',3);coarse=bits('XP.b',8);dac=bits('XP.XC.d',6);counts=bits('XP.XC.m',14)
        rows=[]
        for i in np.flatnonzero((st[1:]==3)&(st[:-1]!=3))+1:
            k=np.searchsorted(t,t[i]+20e-9);assert k<len(t) and st[k]==3
            rows.append(dict(time_s=float(t[k]),coarse=int(coarse[k]),dac=int(dac[k]),measured_count=int(counts[k]),rf_mhz=float(d['obscycles'][k]*24)))
        row.update(finite_physical_waveforms=True,points=len(t),eval_snapshots=rows,waveforms_sha256=sha(wave))
    data=dict(protocol=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),result=row,
        boundary='Separate4.8fF/controller candidate; no inheritance of previous functional/noise passes. Frequency is not jitter. Verify remote process, exit marker and hashes independently.')
    out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8');print(json.dumps(row))
if __name__=='__main__':main()
