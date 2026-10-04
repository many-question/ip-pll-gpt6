"""Compare fresh .125 ps six-point probes with their .25 ps dense sources."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_vco_bias_band import read
from analyze_vco_tail_adjusted import measurement

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def normalized(tb):
    tb=tb.replace('values=[10k 100k 1M 10M 100M 492M]','start=10k stop=492M dec=20')
    tb=re.sub(r'\bmaxstep=\S+','maxstep=STEP',tb)
    tb=re.sub(r'\bmaxsideband=\S+','maxsideband=SIDES',tb)
    return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',tb)

def main():
    pp=H/'results/vco_refinement_probe_protocol.json';p=json.loads(pp.read_text());rows=[]
    for c in p['cases']:
        j=R/c['run']/c['case'];src=R/c['source_run']/c['source_case']
        row=dict(variant=c['variant'],case=c['case'],completed=False)
        if not all((x/'result.json').exists() and json.loads((x/'result.json').read_text()).get('local_outputs_sha256') for x in [j,src]):
            rows.append(row);continue
        manifests=[json.loads((x/'result.json').read_text()) for x in [j,src]]
        row['completed']=True;row['simulator_succeeded']=all(r['ok'] for r in manifests)
        if not row['simulator_succeeded']:rows.append(row);continue
        dep=lambda x:{k:v for k,v in json.loads((x/'result.json').read_text())['inputs_sha256'].items() if k!=x.name+'.scs'}
        assert dep(j)==dep(src)
        assert normalized((j/'inputs'/(j.name+'.scs')).read_text())==normalized((src/'inputs'/(src.name+'.scs')).read_text())
        b,s=read(src);n=measurement(j)
        ix=[int(np.argmin(abs(s['f']/f-1))) for f in n['offsets_hz']]
        assert np.allclose(s['f'][ix],n['offsets_hz'],rtol=1e-8,atol=0)
        old=2*s['L'][ix]/(2*np.pi*b['rf_hz'])**2
        delta=10*np.log10(np.array(n['timing_psd_s2_per_hz'])/old)
        fr=n['rf_hz']/b['rf_hz']-1
        checks=dict(carrier=abs(fr)<p['limits']['relative_rf_change'],sampled_noise=max(abs(delta))<p['limits']['max_absolute_timing_psd_change_db'])
        row.update(baseline=b,refined=n,physical_inputs_verified=True,relative_rf_change=fr,
                   offsets_hz=n['offsets_hz'],timing_psd_change_db=delta.tolist(),max_absolute_psd_change_db=float(max(abs(delta))),
                   checks={k:bool(v) for k,v in checks.items()},sparse_precision_passed=bool(all(checks.values())))
        rows.append(row)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),cases=rows,complete=all(x['completed'] for x in rows),
             full_grid_precision_accepted=False,integrated_jitter_fs=None,full_pll_acceptance=False,limitations=p['limitations'])
    if all(x.get('refined') for x in rows):
        b,n=[x['refined'] for x in rows]
        fr=n['rf_hz']/b['rf_hz']-1
        out['refined_candidate_comparison']=dict(relative_rf_change=fr,frequency_match_passed=abs(fr)<1e-4,
            timing_psd_change_db=(10*np.log10(np.array(n['timing_psd_s2_per_hz'])/b['timing_psd_s2_per_hz'])).tolist())
    (H/'results/vco_refinement_probe_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in out.items() if k!='cases'},'cases':[{k:v for k,v in r.items() if k not in ['baseline','refined']} for r in rows]},indent=2))

if __name__=='__main__':main()
