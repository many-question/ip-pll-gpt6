"""Independent waveform measurements against immutable run inputs."""
from pathlib import Path
import re,json,argparse
import numpy as np
from functools import lru_cache
H=Path(__file__).resolve().parent
DELIVERY=H.parents[2]
ROOT=DELIVERY.parent if DELIVERY.name=='share' and (DELIVERY.parent/'AGENTS.md').exists() else DELIVERY
R=ROOT/'research/runs/spectre_vco_v4'

def cross(t,v,level=0):
    i=np.flatnonzero((v[:-1]<level)&(v[1:]>=level))
    return t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])

def endpoint_windows(tb):
    if '160n 0.2 165n' in tb:return [(110e-9,150e-9),(240e-9,280e-9)]
    return [(150e-9,190e-9),(350e-9,390e-9)] if '200n 0.2 205n' in tb else [(50e-9,90e-9),(160e-9,200e-9)]

@lru_cache(maxsize=1)
def load_data(path):
    with np.load(path) as z:
        return {k:z[k] for k in z.files}

def measure(p,window=None):
    rec=json.loads((p/'result.json').read_text())
    result=dict(run=p.parent.name,case=p.name,sim_ok=rec['ok'],remote_hash_match=rec.get('remote_inputs_match'))
    if not rec['ok']:return result
    d=load_data(p/'waveforms.npz');tb=(p/'inputs'/f'{p.name}.scs').read_text()
    if 'time' not in d or 'tran tran' not in tb:return result
    t=d['time'];a=d['vp']-d['vn']
    start,finish=window or (max(t[-1]-.05e-6,t[-1]*.6),t[-1])
    sel=(t>=start)&(t<=finish)
    ts=t[sel];v=a[sel];edges=cross(ts,v);period=np.diff(edges)
    pp=float(np.ptp(v));freq=float(1/np.mean(period)) if len(period)>3 and pp>.01 else None
    early=np.ptp(a[(t>=start)&(t<(start+finish)/2)]);late=np.ptp(a[(t>=(start+finish)/2)&(t<=finish)])
    result.update(f_ghz=freq/1e9 if freq else None,diff_pp_v=pp,cm_v=float(np.mean((d['vp'][sel]+d['vn'][sel])/2)),
                  tank_min_v=float(min(d['vp'][sel].min(),d['vn'][sel].min())),tank_max_v=float(max(d['vp'][sel].max(),d['vn'][sel].max())),
                  envelope_change=float(late/early-1),period_peak_error=float(np.max(abs(period/np.mean(period)-1))) if len(period)>3 else None,
                  window_s=[float(ts[0]),float(ts[-1])])
    for signal,label in [('VDD:p','total_mw'),('VVCO:p','vco_mw')]:
        if signal in d:result[label]=float(-1.2*np.trapezoid(d[signal][sel],ts)/(ts[-1]-ts[0])*1e3)
    if 'out' in d:
        divider=re.search(r'XD \(vp vn rst (.*?) out',tb).group(1).split()
        m=[4,6,8,10,12,14][divider.index('vdd')]
        out=cross(ts,d['out'][sel],.6);op=np.diff(out)
        fo=1/np.mean(op) if len(op)>3 else None
        ratioerr=(fo*m/freq-1) if fo and freq else None
        # Every period must match; a mean-only frequency check can hide slips.
        perioderr=float(np.max(abs(op*freq/m-1))) if freq and len(op)>3 else None
        result.update(m=m,out_mhz=float(fo/1e6) if fo else None,ratio_error=ratioerr,out_period_peak_error=perioderr,
                      divide_valid=bool(pp>.05 and ratioerr is not None and abs(ratioerr)<.001 and perioderr<.02))
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--runs',nargs='*');args=ap.parse_args()
    data=[]
    for p in sorted(R.glob('*/*/result.json')):
        if args.runs and p.parent.parent.name not in args.runs:continue
        x=measure(p.parent);data.append(x)
        if 'f_ghz' in x:print(f"{x['run']:18s} {x['case']:34s} f={x['f_ghz']} pp={x['diff_pp_v']:.4f} P={x['vco_mw']:.3f} / {x['total_mw']:.3f} valid={x.get('divide_valid')} env={x['envelope_change']:.3f}")
        else:print(x)
    if not args.runs:(H/'results/measurements.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':main()
