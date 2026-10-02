"""Internal frequency, threshold dwell time and slew; no noise inference from slew alone."""
import json
import numpy as np
from analyze import H,R,parse,cross


def main():
    rows=[]
    for rp in sorted(R.glob('*/*/result.json')):
        rec=json.loads(rp.read_text())
        if not rec.get('remote_inputs_match') or not rec['ok']:
            continue
        job=rp.parent; p=job/(job.name+'.raw')/'pss.td.pss'
        if p.exists(): d=parse(p)
        else:
            with np.load(job/'waveforms.npz') as z:d=dict(z)
        t=d['time']; nodes={}; duplicates={}
        for k,v in d.items():
            if k in ['time','units'] or ':' in k:continue
            if len(v)!=len(t):
                assert len(v)%len(t)==0,(job.name,k,len(v),len(t))
                copies=len(v)//len(t); matrix=v.reshape(len(t),copies)
                # Some exploratory save lists name q0 more than once. PSF repeats
                # that scalar at each time; collapse only after exact equality.
                assert np.array_equal(matrix,np.repeat(matrix[:,:1],copies,axis=1)),(job.name,k,'unequal duplicate trace')
                v=matrix[:,0];duplicates[k]=copies
            level=.6 if k not in ['vp','vn'] and not k.endswith('.g0') else (max(v)+min(v))/2
            edges=cross(t,v,level); idx=np.flatnonzero((v[:-1]<level)&(v[1:]>=level))
            nodes[k]=dict(min_v=float(min(v)),max_v=float(max(v)),threshold_v=float(level),
                rising_edges=len(edges), mean_frequency_hz=float(1/np.mean(np.diff(edges))) if len(edges)>1 else None,
                above_threshold_fraction=float(np.trapezoid((v>level).astype(float),t)/(t[-1]-t[0])),
                median_rising_slope_v_per_ns=float(np.median(np.diff(v)[idx]/np.diff(t)[idx])*1e-9) if len(idx) else None)
        rows.append(dict(case=job.name,run=job.parent.name,observation_s=float(t[-1]-t[0]),exact_duplicate_traces_collapsed=duplicates,nodes=nodes))
    (H/'results/node_analysis.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    print('Node records:',len(rows))


if __name__=='__main__':main()
