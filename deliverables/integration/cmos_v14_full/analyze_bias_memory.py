"""Diagnose fixed-code frequency drift during the earlier FLL trajectory.

This is a stopped, superseded fixedM4 diagnostic, not current capture acceptance.
It tests whether the10us bias RC has settled during each~1.8us SAR measurement.
Correlation does not establish sole causality;4ps functional numerics apply.
"""
from pathlib import Path
import json,hashlib,numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
p=ROOT/'research/runs/spectre_cmos_v14_full/acquire01/acquire_k41_tt/waveforms.npz'
with np.load(p) as z:d={k:z[k] for k in z.files if k!='units'}
t=d['time'];code=np.zeros(len(t),int);dac=code.copy()
for target,prefix,n in [(code,'XP.b',8),(dac,'XP.XC.d',6)]:
 for i in range(n):target[:]+=((d[prefix+str(i)]>.6).astype(int)<<i)
bound=np.r_[0,np.flatnonzero((np.diff(code)!=0)|(np.diff(dac)!=0))+1,len(t)]
obs=np.flatnonzero(abs(np.diff(d['obscycles']))>1e-9)+1;rows=[]
for a,b in zip(bound[:-1],bound[1:]):
 if t[b-1]-t[a]<.9e-6:continue
 lo=t[a]+.45e-6;hi=t[b-1]-.05e-6
 first=obs[(t[obs]>=lo)&(t[obs]<lo+.2e-6)];last=obs[(t[obs]>hi-.2e-6)&(t[obs]<=hi)]
 if min(len(first),len(last))<3:continue
 f1=float(np.mean(d['obscycles'][first])*24);f2=float(np.mean(d['obscycles'][last])*24)
 m1=(t>=lo)&(t<lo+.2e-6);m2=(t>hi-.2e-6)&(t<=hi)
 v1=float(np.mean(d['XP.XV.XL.nfilt'][m1]));v2=float(np.mean(d['XP.XV.XL.nfilt'][m2]));nb=float(np.mean(d['XP.XV.XL.nb'][a:b]))
 rows.append(dict(coarse=int(code[a]),dac=int(dac[a]),plateau_us=[float(t[a]*1e6),float(t[b-1]*1e6)],sample_centers_us=[float((lo+.1e-6)*1e6),float((hi-.1e-6)*1e6)],rf_mhz=[f1,f2],rf_change_mhz=f2-f1,nfilt_v=[v1,v2],nfilt_change_mv=(v2-v1)*1e3,nb_v=nb,final_bias_offset_mv=(v2-nb)*1e3,mainloop_enable_at_samples=[bool(np.mean(d['XP.en'][m1])>.6),bool(np.mean(d['XP.en'][m2])>.6)]))
out=dict(scope=__doc__,source=str(p.relative_to(ROOT)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bias_filter=dict(r_ohm=1e6,c_f=10e-12,tau_us=10),plateaus=rows,interpretation='Read fixed-code measured drift against3MHz RF counter quantum. Bias memory is a candidate contributor; do not declare the present programmable cold run failed from this superseded diagnostic.')
fine=[r for r in rows if r['dac']!=11 and not any(r['mainloop_enable_at_samples'])]
out['fine_search_max_observed_plateau_drift_mhz']=max(abs(r['rf_change_mhz']) for r in fine)
out['interpretation']='The10us bias RC retains history, but measured within-plateau drift during late fine search is only about0.03–0.12MHz, much smaller than3MHz counter quantum. It does not by itself explain the observed~3.4MHz handoff residual. The last plateau spans CP enable and must not be used as an isolated bias-only experiment. Current programmable reset trajectory remains the authority.'
(H/'results/bias_memory_diagnostic.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(rows,indent=2))
