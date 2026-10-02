"""Independent RC thermal-noise calibration for the exact164MHz/ratio6 setup."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
job=ROOT/'research/runs/spectre_cmos_v14_full/noisecal01/noise_measurement_fixture'
rec=json.loads((job/'result.json').read_text());assert rec['remote_inputs_match'] and rec['ok']
raw=job/(job.name+'.raw');p=raw/'pnMedge.0.sample.pnoise'
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def header(k):return float(re.search('"'+re.escape(k)+'"\\s+([0-9.eE+\\-]+)',p.read_text())[1])
d=parse(p);f=d['freq'];slew=header('slew rate event_1');st=d['out']**2/slew**2
full=float(np.sqrt(np.trapezoid(st,f))*1e15)
jee=float(parse(raw/'pnMedge.0.Jee.pnoise')['Jee'][0])*1e15
clip=f<=82e6;clipped=float(np.sqrt(np.trapezoid(st[clip],f[clip]))*1e15)
kb=1.380649e-23;temp=300.15;cap=20e-15;res=1e3;fs=984e6
amplitude=.5/np.sqrt(1+(2*np.pi*fs*res*cap)**2);analytic_slew=2*np.pi*fs*amplitude
rho=np.exp(-1/(fs*res*cap))
sv=2*kb*temp/(cap*fs)*(1-rho*rho)/(1-2*rho*np.cos(2*np.pi*f/fs)+rho*rho)
analytic=float(np.sqrt(np.trapezoid(sv/analytic_slew**2,f))*1e15)
td=parse(raw/'pss.td.pss');t=td['time'];v=td['out'];n=int(np.sum((v[:-1]<.6)&(v[1:]>=.6)))
period_ok=bool(abs((t[-1]-t[0])*164e6-1)<1e-8 and n==6 and abs(v[-1]-v[0])<1e-3)
result=dict(scope=__doc__,source_result=str((job/'result.json').relative_to(ROOT)),circuit='1kohm/20fF first-order RC,27C,noiseless984MHz sinusoid0.5V amplitude+0.6VDC. Not a PLL noise result.',
 pss_fund_hz=164e6,sample_ratio=header('sample ratio factor'),sample_rate_hz=fs,rising_edges=n,periodic_passed=period_ok,band_hz=[float(f[0]),float(f[-1])],
 explicit_integral_fs=full,analytic_integral_fs=analytic,relative_to_analytic=full/analytic-1,spectre_auto_jee_fs=jee,auto_jee_grid_cutoff_hz=float(f[clip][-1]),grid_clipped_integral_fs=clipped,clipped_relative_to_auto_jee=clipped/jee-1,
 passed=bool(period_ok and header('sample ratio factor')==6 and abs(full/analytic-1)<.005 and abs(clipped/jee-1)<.015),
 interpretation='AutoJee does not integrate through492MHz for the164MHz PSS superperiod. Explicit PSD/slew-squared integration supplies the requested band; cross-check autoJee only over its actual clipped grid. This identical-edge LTI fixture does not establish edge-position invariance in the real chain.')
(H/'results/noise_measurement_fixture.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
