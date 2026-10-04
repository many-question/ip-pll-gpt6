"""Calibrate long-superperiod noise conversion with independent analytic RC covariance."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from noise_utils import parse,header,cross,devices
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--protocol',default='core_noise_calibration_protocol.json');args=parser.parse_args()
assert Path(args.protocol).name==args.protocol and args.protocol.endswith('.json')
p=json.loads((H/'results'/args.protocol).read_text());limits=p['limits'];rows=[]
for item in p['cases']:
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(case=item['case'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),passed=False);rows.append(row)
    log=(j/'spectre.out').read_text()
    if not r['ok'] or 'spectre completes with 0 errors' not in log:continue
    assert r['remote_inputs_match'] and not r.get('periodic_state') and 'The steady-state solution was achieved' in log
    # The runner normalizes newlines. Check immutable source SHA and exact text,
    # rather than incorrectly requiring CRLF source bytes to equal LF uploads.
    tb=H/'tb'/(item['case']+'.scs');assert sha(tb)==item['tb_sha256']
    assert (j/'inputs'/tb.name).read_text()==tb.read_text()
    assert re.search(r'^\s*method\s*=\s*gear2only\s*$',log,re.M)
    raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');time=td['time'];n=len(cross(time,td['out']))
    period_ok=bool(abs((time[-1]-time[0])*p['fund_hz']-1)<limits['period_relative'] and n==246 and abs(td['out'][-1]-td['out'][0])<limits['endpoint_v'])
    pn=raw/'pnMedge.0.sample.pnoise';noise=parse(pn);freq=noise['freq'];slope=header(pn,'slew rate event_1');ratio=header(pn,'sample ratio factor')
    assert slope>0 and np.all(np.diff(freq)>0) and abs(freq[0]/1e4-1)<1e-8 and abs(freq[-1]/492e6-1)<1e-8
    if p.get('offsets_hz'):assert np.allclose(freq,p['offsets_hz'],rtol=1e-10,atol=0)
    sv=noise['out']**2;st=sv/slope**2;rms=float(np.sqrt(np.trapezoid(st,freq))*1e15)
    dev=devices(pn,len(freq));ds=float(max(abs(sum(dev.values())/sv-1)));assert ds<1e-7
    fs=p['sample_frequency_hz'];res=p['resistance_ohm'];cap=p['capacitance_f'];kb=1.380649e-23;temp=p['temperature_k']
    amplitude=.5/np.sqrt(1+(2*np.pi*fs*res*cap)**2);analytic_slope=2*np.pi*fs*amplitude;rho=np.exp(-1/(fs*res*cap))
    analytic_sv=2*kb*temp/(cap*fs)*(1-rho*rho)/(1-2*rho*np.cos(2*np.pi*freq/fs)+rho*rho)
    ar=float(np.sqrt(np.trapezoid(analytic_sv/analytic_slope**2,freq))*1e15)
    point_db=float(max(abs(10*np.log10(st/(analytic_sv/analytic_slope**2)))))
    auto=float(parse(raw/'pnMedge.0.Jee.pnoise')['Jee'][0])*1e15
    mask=freq<=p['fund_hz']/2;cr=float(np.sqrt(np.trapezoid(st[mask],freq[mask]))*1e15)
    row.update(periodic_passed=period_ok,rising_edges=n,sample_ratio=ratio,band_hz=[float(freq[0]),float(freq[-1])],offsets_hz=freq.tolist(),
        timing_psd_s2_per_hz=st.tolist(),explicit_rms_fs=rms,analytic_rms_fs=ar,analytic_error=rms/ar-1,
        auto_jee_fs=auto,clipped_grid_rms_fs=cr,clipped_grid_max_hz=float(freq[mask][-1]),clipped_auto_error=cr/auto-1,
        device_sum_relative_error=ds,raw_noise_sha256=sha(pn),slew_v_per_s=slope,analytic_slew_v_per_s=analytic_slope,
        max_point_psd_error_db_to_analytic=point_db,
        passed=bool(period_ok and ratio==246 and abs(rms/ar-1)<limits['rms_relative_to_analytic'] and point_db<limits.get('point_psd_db_to_analytic',.1) and abs(cr/auto-1)<limits['clipped_vs_auto_jee_relative']))
out=dict(scope=__doc__,cases=rows,complete=len(rows)==2,passed=False,not_pll_performance=True,full_pll_acceptance=False)
if out['complete'] and all('explicit_rms_fs' in x for x in rows):
    a,b=rows;assert np.allclose(a['offsets_hz'],b['offsets_hz'],rtol=1e-10,atol=0)
    relative=a['explicit_rms_fs']/b['explicit_rms_fs']-1;delta=10*np.log10(np.array(a['timing_psd_s2_per_hz'])/b['timing_psd_s2_per_hz'])
    out['core_to_fine']=dict(rms_relative_difference=relative,max_psd_difference_db=float(max(abs(delta))),passed=bool(abs(relative)<limits['core_to_fine_rms_relative'] and max(abs(delta))<limits['core_to_fine_psd_db']))
    out['passed']=bool(all(x['passed'] for x in rows) and out['core_to_fine']['passed'])
(H/'results'/p.get('output','core_noise_calibration_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(complete=out['complete'],passed=out['passed'],comparison=out.get('core_to_fine'),cases=[{k:v for k,v in x.items() if k not in ['offsets_hz','timing_psd_s2_per_hz']} for x in rows]),indent=2))
