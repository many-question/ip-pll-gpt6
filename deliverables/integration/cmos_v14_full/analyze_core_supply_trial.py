"""Audit the stopped supply-corrected shooting trial and its saved stable segment."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/coretripsupply01/core_pulsetrip_supply_noise_tt'
log=(j/'spectre.out').read_text(errors='replace');rec=json.loads((j/'result.json').read_text())
assert not rec['ok'] and rec['remote_inputs_match'] and 'SPECTRE-25' in log
raw=j/(j.name+'.raw');source=raw/'pss.tran.pss';cache=j/'tstab_last_period.npz'
keys=['out','XP.vp','XP.vn','XP.ctrl','XP.refb','XP.clk','XP.q1','XP.data','XP.XD.d8','XP.XD.d12','XP.XD.d6','XP.XD.ck','XP.XD.load','XP.XD.loadb']
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()
if not cache.exists():
    with source.open('rb') as f:
        f.seek(max(0,source.stat().st_size-1024*1024))
        times=re.findall(rb'^"time"\s+([0-9.eE+\-]+)',f.read(),re.M)
    assert times;end=float(times[-1]);begin=end-250e-9
    cols={k:[] for k in ['time']+keys};record={};active=False;within=False;duplicates=0
    def flush():
        if not record:return
        assert set(cols)<=set(record),record.get('time')
        for k in cols:cols[k].append(record[k])
    with source.open() as f:
        for line in f:
            if not active:
                if line.strip()=='VALUE':active=True
                continue
            if line.startswith('"time" '):
                flush();record={};t=float(line.split()[1]);within=t>=begin-2e-12
                if within:record['time']=t
            elif within:
                z=line.split()
                if len(z)!=2:continue
                k=z[0].strip('"')
                if k in cols:
                    if k in record:duplicates+=1
                    record[k]=float(z[1])
    flush()
    d={k:np.asarray(v) for k,v in cols.items()}
    assert np.all(np.diff(d['time'])>0) and d['time'][0]<=begin and abs(d['time'][-1]-end)<1e-15
    np.savez_compressed(cache,**d,begin_s=begin,end_s=end,duplicate_fields=duplicates,source_sha256=sha(source))
with np.load(cache) as z:d={k:z[k] for k in z.files}
t=d['time'];a=float(d['begin_s']);b=float(d['end_s']);ix=(t>=a)&(t<=b)
expected={'out':246,'XP.refb':6,'XP.clk':984,'XP.q1':492,'XP.data':246,'XP.XD.d8':123,'XP.XD.d12':82,'XP.XD.d6':164,'XP.XD.ck':492}
branches={}
for k,count in expected.items():
    e=cross(t,d[k]);e=e[(e>=a)&(e<b)]
    p=np.diff(np.r_[e,e[0]+b-a]) if len(e) else np.array([0.])
    branches[k]=dict(rising_edges=len(e),expected=count,max_period_fraction_error=float(max(abs(p*count/(b-a)-1))))
out=dict(scope=__doc__,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'),
    cancellation=json.loads((j/'cancellation.json').read_text()),convergence_history=re.findall(r'^Conv norm.*$',log,re.M),
    raw_tstab=dict(path=source.relative_to(ROOT).as_posix(),bytes=source.stat().st_size,sha256=str(d['source_sha256'])),
    last_saved_period_us=[a*1e6,b*1e6],branches=branches,
    endpoint_delta_v={k:float(np.interp(b,t,d[k])-np.interp(a,t,d[k])) for k in keys},
    ranges_v={k:[float(min(d[k][ix])),float(max(d[k][ix]))] for k in keys},
    segmentation_fault_after_stop='SPECTRE-18' in log and log.index('SPECTRE-18')>log.index('SPECTRE-25'),
    pnoise_ran=bool(list(raw.glob('*.pnoise'))),periodic_state_valid=False,full_pll_acceptance=False,
    interpretation='Three-node IC correction removes the initial impulse, but subsequent shooting norms75.3k,340k,2.1M do not converge in the observed trial. Deliberately stoppedafter4norms,notproofperiodicsolutiondoesnotexist. Tightitres-onlycomparisonisrunning; finalaccuracyunchanged.')
(H/'results/core_supply_trial_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['convergence_history','last_saved_period_us','branches','endpoint_delta_v','pnoise_ran','segmentation_fault_after_stop']},indent=2))
