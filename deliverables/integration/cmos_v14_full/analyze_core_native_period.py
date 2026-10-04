"""Check two observer-free 250ns periods after exact native restoration at 3us."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
from psf_trace_units import trace_units

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();assert re.fullmatch(r'[A-Za-z0-9_]+',a.run)
    p=json.loads((H/'results/core_plain_warm_protocol.json').read_text());case=p['case']
    src=R/p['run']/case;j=R/a.run/case;rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Pending native result');return
    old=json.loads((src/'result.json').read_text());r=json.loads(rp.read_text())
    for folder,record in [(src,old),(j,r)]:
        assert record['ok'] and record['remote_inputs_match'] and 'spectre completes with 0 errors' in (folder/'spectre.out').read_text()
        assert sha(folder/'final.ic')==record['local_outputs_sha256']['final.ic']
        assert all(sha(folder/'inputs'/k)==v for k,v in record['inputs_sha256'].items())
    assert {k:v for k,v in r['inputs_sha256'].items() if k!=case+'.scs'}=={k:v for k,v in old['inputs_sha256'].items() if k!=case+'.scs'}
    n=r['native_state'];checkpoint=ROOT/n['local'];proof=json.loads(checkpoint.with_suffix('.json').read_text())
    assert sha(checkpoint)==n['sha256']==proof['sha256'] and n['remote_hash_match'] and n['source_snapshot']==p['run']
    assert proof['source_result_sha256']==sha(src/'result.json')
    body=(j/'inputs'/(case+'.scs')).read_text();base=(src/'inputs'/(case+'.scs')).read_text()
    def canonical(s):
        s=re.sub(r'\s+(readic|recover)="[^"]+"','',s)
        s=re.sub(r'(writefinal|savefile)="[^"]+"',r'\1="PATH"',s)
        return re.sub(r'\b(stop|skipcount)=\S+',r'\1=VALUE',s)
    assert canonical(body)==canonical(base)
    assert 'XOBS' not in body and 'strobeperiod' not in body and 'skipcount=0' in body and 'readic=' not in body
    log=(j/'spectre.out').read_text();assert 'Recovering from save-restart file '+n['remote'] in log
    assert re.search(r'^\s*method\s*=\s*gear2only\s*$',log,re.M)
    assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    t=d['time'];start=3e-6;T=250e-9;end=start+2*T
    assert abs(t[0]-start)<1e-14 and abs(t[-1]-end)<1e-14 and np.all(np.diff(t)>0)
    units=trace_units(j/(case+'.raw')/'tran.tran.tran')
    assert units==trace_units(src/(case+'.raw')/'tran.tran.tran')
    grid=np.linspace(start,start+T,250001);rows=[];branches=[]
    for k,u in units.items():
        delta=np.interp(grid+T,t,d[k])-np.interp(grid,t,d[k])
        rows.append(dict(node=k,unit=u,peak=float(max(abs(delta))),rms=float(np.sqrt(np.mean(delta**2)))))
        if k in p['expected_rising_edges_per_period']:
            e=cross(t,d[k]);ea=e[(e>=start)&(e<start+T)];eb=e[(e>=start+T)&(e<end)];count=p['expected_rising_edges_per_period'][k]
            row=dict(node=k,first_edges=len(ea),second_edges=len(eb),expected=count,passed=len(ea)==len(eb)==count)
            if row['passed']:
                shift=(eb-ea-T)*1e12;row.update(mean_displacement_ps=float(np.mean(shift)),peak_displacement_ps=float(max(abs(shift))))
            branches.append(row)
    def state(path):
        found={}
        for line in path.read_text().splitlines():
            z=line.split()
            if z and z[0] in p['physical_state_units']:
                u='A' if re.search(r'#unit\s+A\s*$',line) else 'V'
                assert u==p['physical_state_units'][z[0]];found[z[0]]=float(z[1])
        assert set(found)==set(p['physical_state_units']);return found
    initial=state(src/'final.ic');final=state(j/'final.ic')
    endpoints=[dict(node=k,unit=u,difference=final[k]-initial[k]) for k,u in p['physical_state_units'].items()]
    volts=sorted([x for x in rows if x['unit']=='V'],key=lambda x:-x['peak'])
    ev=sorted([x for x in endpoints if x['unit']=='V'],key=lambda x:-abs(x['difference']))
    rf=fit_edges(cross(t,d['XP.vp']-d['XP.vn'],0));of=fit_edges(cross(t,d['out']))
    held=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
    lim=p['limits'];counts=all(x['passed'] for x in branches);assert len(branches)==11
    dense=volts[0]['peak']<lim['dense_voltage_difference_peak_v'];ends=abs(ev[0]['difference'])<lim['all_state_voltage_endpoint_difference_v']
    carrier=abs(rf['carrier_hz']/3936e6-1)<lim['carrier_relative_error'] and abs(of['carrier_hz']/984e6-1)<lim['carrier_relative_error']
    out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),native_source_sha256=n['sha256'],
        dense_periods_passed=bool(dense),all_state_endpoint_screen_passed=bool(ends),carrier_screen_passed=bool(carrier),
        branch_counts_passed=counts,coarse23_held=bool(held),ready_for_pss_review=bool(dense and ends and carrier and counts and held),
        rf_fit=rf,output_fit=of,branches=branches,all_dense_rows=rows,all_state_endpoint_rows=endpoints,
        largest_dense_voltage_mismatches=volts[:12],largest_endpoint_voltage_mismatches=ev[:12],
        periodic_state_valid=False,random_jitter_measured=False,full_pll_acceptance=False,
        limitations=['Working1mV/10ppm screens are not PSS or Gear2 numerical convergence.','Native restart preserves prior numerical history; no phase alignment or state correction used.','No random-noise calculation in this deterministic run.'])
    (H/'results/core_native_period_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['all_dense_rows','all_state_endpoint_rows','branches']},indent=2))

if __name__=='__main__':main()
