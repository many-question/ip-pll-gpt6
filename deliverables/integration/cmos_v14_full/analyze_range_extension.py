"""Validate loaded-oscillator endpoints independently of divider function."""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full/range48_01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for p in sorted(R.glob('*/result.json')):
 j=p.parent;r=json.loads(p.read_text())
 if not r.get('local_outputs_sha256'):continue
 assert r['remote_inputs_match'] and r['ok'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
 assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
 with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 t=d['time'];assert t[0]>=339.999e-9 and t[-1]>=399.999e-9
 assert 'unit_c=4.8f' in (j/'inputs'/(j.name+'.scs')).read_text()
 _,code,ctrl,corner=j.name.split('_');code=int(code[1:]);ratio=14 if code else 4
 e=cross(t,d['vp']-d['vn'],0);o=cross(t,d['out']);rf=float(1e-6/np.mean(np.diff(e)));fo=float(1e-6/np.mean(np.diff(o))) if len(o)>2 else None
 power={k:float((d['energy_'+k+'_nj'][-1]-d['energy_'+k+'_nj'][0])/((t[-1]-t[0])*1e6)) for k in ['total','vco','rx','rt']}
 power['other']=power['total']-power['vco']-power['rx']-power['rt']
 dense=float(-1.2*np.trapezoid(d['VDD:p'],t)/(t[-1]-t[0])*1e3);assert abs(dense/power['total']-1)<.002
 halves=[]
 for a,b in [(340e-9,370e-9),(370e-9,400e-9)]:
  ee=e[(e>=a)&(e<=b)];halves.append(float(1e-6/np.mean(np.diff(ee))))
 rows.append(dict(case=j.name,source_result=p.relative_to(ROOT).as_posix(),source_sha256=sha(p),corner=corner,code=code,ctrl_v=.2 if ctrl=='v02' else 1,rf_mhz=rf,rf_half_window_mhz=halves,output_mhz=fo,
  oscillator_endpoint_covered=bool(rf<=2688 if code else rf>=3936),divider_frequency_ratio_ok=bool(fo and abs(fo*ratio/rf-1)<.001),
  differential_swing_pp_v=float(np.ptp(d['vp']-d['vn'])),partial_fixture_power_mw=power,dense_power_crosscheck_mw=dense))
out=dict(cases=rows,expected=6,full_pll_acceptance=False,scope='Loaded VCO with original MOS bank,unit capacitor4.8fF,external coarse/control; endpoints only. No intermediate-code continuity, FLL or fullPLL jitter/power signoff.')
(H/'results/range_extension_validation.json').write_text(json.dumps(out,indent=2)+'\n')
for r in rows:print(r['case'],r['rf_mhz'],r['oscillator_endpoint_covered'],r['divider_frequency_ratio_ok'])
