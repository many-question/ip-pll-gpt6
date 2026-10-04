"""Compare short warm current trajectories; no random-noise interpretation."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];p=json.loads((H/'results/core_method_probe_protocol.json').read_text())
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest();rows=[];waves={};deps=None
grid=5e-9+np.arange(60000)*.25e-12;f=np.fft.rfftfreq(len(grid),.25e-12);w=np.hanning(len(grid))
finegrid=5e-9+np.arange(120000)*.125e-12;finefreq=np.fft.rfftfreq(len(finegrid),.125e-12);finewindow=np.hanning(len(finegrid))
for item in p['cases']:
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(case=item['case'],method=item['method'],maxstep_s=item['maxstep_s'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),simulation_completed=False);rows.append(row)
    log=(j/'spectre.out').read_text()
    if not r['ok'] or 'spectre completes with 0 errors' not in log:continue
    assert re.search(r'^\s+method\s*=\s*'+item['method']+r'\s*$',log,re.M)
    step=re.findall(r'^\s+maxstep\s*=\s*([\d.eE+-]+)\s+(fs|ps|ns)\s*$',log,re.M)
    assert step and abs(float(step[-1][0])*dict(fs=1e-15,ps=1e-12,ns=1e-9)[step[-1][1]]/item['maxstep_s']-1)<1e-9
    assert r['remote_inputs_match'] and r['inputs_sha256']['core_pulsetrip_late_seed_tt.ic']==p['seed_sha256']
    current={k:v for k,v in r['inputs_sha256'].items() if k!=item['case']+'.scs'}
    if deps is None:deps=current
    assert deps==current
    wp=j/'waveforms.npz';assert sha(wp)==r['local_outputs_sha256']['waveforms.npz']
    with np.load(wp) as z:d={k:z[k] for k in z.files}
    t=d['time'];assert abs(t[0]-5e-9)<1e-14 and abs(t[-1]-20e-9)<1e-14
    rf_edges=cross(t,d['XP.vp']-d['XP.vn'],0);out_edges=cross(t,d['out']);assert len(rf_edges)>40 and len(out_edges)>10
    metrics={};ys={}
    for k in ['XP.vp','out','VDD:p','XP.VVCO:p','XP.VRX:p','XP.VRT:p']:
        y=np.interp(grid,t,d[k]);ys[k]=y;a=abs(np.fft.rfft((y-y.mean())*w))**2
        fy=np.interp(finegrid,t,d[k]);fa=abs(np.fft.rfft((fy-fy.mean())*finewindow))**2
        high=(f>=100e9)&(f<=1500e9);finehigh=(finefreq>=100e9)&(finefreq<=1500e9)
        metrics[k]=dict(mean=float(np.mean(y)),peak_to_peak=float(np.ptp(y)),
            deterministic_highband_fraction_100_500GHz=float(sum(a[(f>=100e9)&(f<=500e9)])/sum(a)),
            deterministic_highband_fraction_250_500GHz=float(sum(a[(f>=250e9)&(f<=500e9)])/sum(a)),
            deterministic_highband_fraction_500_1500GHz=float(sum(a[(f>=500e9)&(f<=1500e9)])/sum(a)),
            deterministic_highband_fraction_100_1500GHz=float(sum(a[high])/sum(a)),
            highband_peak_frequency_hz=float(f[high][np.argmax(a[high])]),
            finegrid_fraction_100_1500GHz=float(sum(fa[finehigh])/sum(fa)))
    row.update(simulation_completed=True,rf_hz=float(1/np.mean(np.diff(rf_edges))),output_hz=float(1/np.mean(np.diff(out_edges))),
        rf_swing_pp_v=float(np.ptp(d['XP.vp']-d['XP.vn'])),accepted_step_quantiles_ps=np.quantile(np.diff(t),[.1,.5,.9,1]).tolist(),metrics=metrics)
    row['accepted_step_quantiles_ps']=[x*1e12 for x in row['accepted_step_quantiles_ps']]
    waves[item['case']]=ys
comparisons=[]
for method in ['trap','gear']:
    a,b=[f'coremethod_{method}_{s}_tt' for s in ['1ps','halfps']]
    if a in waves and b in waves:
        comparisons.append(dict(coarse=a,fine=b,unshifted_waveform_difference={k:dict(rms=float(np.sqrt(np.mean((waves[a][k]-waves[b][k])**2))),peak=float(max(abs(waves[a][k]-waves[b][k])))) for k in waves[a]}))
out=dict(scope=__doc__,condition=p['condition'],cases=rows,mesh_comparisons=comparisons,complete=len(rows)==4,
    uniform_grid_step_ps=.25,regridding_control_ps=.125,spectral_window='Hann',full_pll_acceptance=False,random_jitter_measured=False,
    interpretation='Numerical waveform check only. Compare100-1500GHz as well as100-500GHz: reducing the time step can shift trapezoidal alternating-step artifacts above500GHz. Common-time differences include phase/frequency shifts; no tolerance is relaxed and no integration method is accepted solely because it has a smoother current. The15ns window is shorter than one reference cycle; its mean RF frequency is not a locked carrier estimate.')
(H/'results/core_method_probe_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(complete=out['complete'],cases=[{k:v for k,v in r.items() if k!='metrics'} for r in rows]),indent=2))
