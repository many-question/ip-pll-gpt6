"""Quantify measured finite harmonic neighbourhoods without inventing a cutoff.

Reads separately completed main and neighbour analyses from the same fresh
PSS job, even when its client observer timed out. No whole-job success is
fabricated and no unmeasured interval is counted as zero noise.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,header,devices,selected_device_components
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=ROOT/'research/runs/spectre_cmos_v14_full/rt4pulsetripband01/chain_rt4_pulsetrip_band_tt'

def load(name):
    folder=j/('completed_'+name+'_snapshot');manifest=folder/'snapshot.json';m=json.loads(manifest.read_text())
    assert m['completed_analysis_collected'] and m['analysis']==name
    assert all(sha(folder/x['name'])==x['sha256'] for x in m['files'])
    assert all(sha(j/'inputs'/k)==v for k,v in m['inputs_sha256'].items())
    path=folder/(name+'Medge.0.sample.pnoise');pn=parse(path);f=pn['freq'];sv=pn['out']**2;slope=header(path,'slew rate event_1')
    assert slope>0 and np.all(np.diff(f)>0) and np.all(np.isfinite(sv)) and np.all(sv>0)
    dev=devices(path,len(f));closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
    return dict(folder=folder,manifest=m,manifest_sha256=sha(manifest),path=path,f=f,st=sv/slope**2,dev={k:x/slope**2 for k,x in dev.items()},slope=slope,closure=closure)

def main():
    if not (j/'completed_pnnear_snapshot/snapshot.json').exists():print('Completed neighbour snapshot pending');return
    a=load('pn');b=load('pnnear')
    assert a['manifest']['inputs_sha256']==b['manifest']['inputs_sha256']
    assert all(sha(a['folder']/name)==sha(b['folder']/name) for name in ['pss.td.pss','pss.fd.pss'])
    assert abs(a['slope']/b['slope']-1)<1e-10
    proof=json.loads((H/'results/rt4_completed_band_validation.json').read_text());assert proof['periodic_passed'] and proof['source_snapshot_sha256']==a['manifest_sha256']
    p=json.loads((H/'results/rt_pulsetrip_noise_protocol.json').read_text());item=next(x for x in p['cases'] if x['case']==j.name)
    assert np.allclose(b['f'],item['harmonic_neighbour_offsets_hz'],rtol=1e-12,atol=0)
    rows=[]
    for harmonic in [164e6,328e6,492e6]:
        for side in [-1,1]:
            index=np.flatnonzero((side*(b['f']-harmonic)>0)&(side*(b['f']-harmonic)<=1e4))
            if harmonic==492e6 and side==1:assert len(index)==0;continue
            index=index[np.argsort(abs(b['f'][index]-harmonic))];delta=abs(b['f'][index]-harmonic);s=b['st'][index]
            # Subtracting a ~500MHz carrier magnifies ASCII frequency roundoff.
            # Keep measured distances and integrate only their actual bounds.
            assert np.allclose(delta,[1,10,100,1000,10000],rtol=0,atol=1e-6)
            top=sorted(b['dev'],key=lambda n:-b['dev'][n][index[0]])[:5]
            typed=selected_device_components(b['path'],top,len(b['f']))
            finite=integral(delta,s,delta[0],delta[-1]);powerlaw=integral(delta,s,delta[0],delta[-1],True)
            bg=np.interp(b['f'][index],a['f'],a['st'])
            rows.append(dict(harmonic_hz=harmonic,side='lower' if side<0 else 'upper',distance_hz=delta.tolist(),
                timing_psd_s2_per_hz=s.tolist(),near_to_main_interpolation_ratio=(s/bg).tolist(),
                innermost_total_psd_log_slope=float(np.log10(s[1]/s[0])),
                finite_window_variance_s2=finite,powerlaw_variance_s2=powerlaw,
                finite_window_rms_fs=float(np.sqrt(finite)*1e15),
                nearest_top_contributors=[dict(device=n,total_fraction=float(b['dev'][n][index[0]]/s[0]),
                    component_fraction_of_device={k:float(v[index[0]]/typed[n]['total'][index[0]]) for k,v in typed[n].items() if k!='total'}) for n in top]))
    out=dict(scope=__doc__,condition=p['condition'],main_snapshot_sha256=a['manifest_sha256'],near_snapshot_sha256=b['manifest_sha256'],
        same_fresh_pss_verified=True,device_sum_relative_error=b['closure'],sides=rows,
        total_finite_neighbour_window_rms_fs=float(np.sqrt(sum(x['finite_window_variance_s2'] for x in rows))*1e15),
        unmeasured_centre_intervals_hz=[[164e6-1,164e6+1],[328e6-1,328e6+1],[492e6-1,492e6]],
        provisional_main_log_grid_rms_fs=proof['provisional_log_grid_rms_fs'],qualified_integrated_rms_fs=None,
        physical_low_frequency_cutoff_assumed=False,physical_pole_integral_closed=False,whole_job_completion_claimed=False,full_pll_acceptance=False,
        limitations=['Finite neighbour windows are measured only down to1Hz distance; the remaining central intervals are unknown, not excised as spurs.',
            'Five points per side do not establish quadrature convergence. Linear and power-law integrals are sensitivity estimates.',
            'Do not add these window integrals directly to the main-grid variance: their frequency ranges overlap.',
            'Actual noisy LC, closed-loop transfer and PVT remain outside this fixture.'])
    (H/'results/rt4_harmonic_neighbour_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
