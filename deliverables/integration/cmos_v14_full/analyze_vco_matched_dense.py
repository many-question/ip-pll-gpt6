"""Validate matched dense VCO spectra and same-workpoint numerical convergence."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_vco_bias_band import read,integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)

def normalized(s):
    s=s.replace('values=[10k 100k 1M 10M 100M 492M]','start=10k stop=492M dec=20')
    s=re.sub(r'maxstep=\S+','maxstep=STEP',s);s=re.sub(r'maxsideband=\S+','maxsideband=SIDES',s)
    return normal(s)

def band(row,s,lo,hi):
    scale=2/(2*np.pi*row['rf_hz'])**2;total=scale*integral(s['f'],s['L'],lo,hi)
    parts={g:scale*integral(s['f'],x,lo,hi) for g,x in s['groups'].items()}
    assert abs(sum(parts.values())/total-1)<1e-9
    return dict(rms_fs=float(np.sqrt(total)*1e15),powerlaw_rms_fs=float(np.sqrt(scale*integral(s['f'],s['L'],lo,hi,True))*1e15),
                group_variance_fraction={g:x/total for g,x in parts.items()})

def main():
    pp=H/'results/vco_matched_dense_protocol.json';p=json.loads(pp.read_text())
    assert sha(H/'results'/p['source_match_validation'])==p['source_match_validation_sha256']
    rows=[];spectra={};lookup={};jobs={}
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json';row=dict(case=c['case'],variant=c['variant'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(row);continue
        result=json.loads(rp.read_text());row.update(completed=True,simulator_passed=result['ok'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp))
        if result['ok']:
            src=R/c['source_run']/c['source_case'];assert sha(src/'result.json')==c['source_result_sha256']
            deps={k:v for k,v in result['inputs_sha256'].items() if k!=j.name+'.scs'};assert deps==c['dependencies_sha256']
            body=(j/'inputs'/(j.name+'.scs')).read_text().replace('start=10k stop=492M dec=20','values=[10k 100k 1M 10M 100M 492M]')
            if c['coarser_numerical_setting']:body=body.replace('maxstep=0.25p','maxstep=0.125p').replace('maxsideband=511','maxsideband=1023')
            assert normal(body)==normal((src/'inputs'/(src.name+'.scs')).read_text())
            measured,s=read(j);row.update(measured,physical_source_verified=True)
            lookup[c['variant']]=row;spectra[c['variant']]=s;jobs[c['variant']]=j
        rows.append(row)
    checks={};lim=p['precision_limits']
    for label,oldkey,newkey in [('baseline','baseline_025','baseline_0125'),('candidate','candidate_025','candidate_0125')]:
        if newkey not in lookup:continue
        if label=='baseline':
            b=p['original_baseline'];j=R/b['run']/b['case'];assert sha(j/'result.json')==b['source_result_sha256']
            lookup[oldkey],spectra[oldkey]=read(j);jobs[oldkey]=j
        if oldkey not in lookup:continue
        a,b=lookup[oldkey],lookup[newkey];x,y=spectra[oldkey],spectra[newkey]
        dep=lambda j:{k:v for k,v in json.loads((j/'result.json').read_text())['inputs_sha256'].items() if k!=j.name+'.scs'}
        ja,jb=jobs[oldkey],jobs[newkey];assert dep(ja)==dep(jb)
        assert normalized((ja/'inputs'/(ja.name+'.scs')).read_text())==normalized((jb/'inputs'/(jb.name+'.scs')).read_text())
        assert np.allclose(x['f'],y['f'],rtol=1e-12,atol=0),'Different sweep grid beyond ASCII roundoff'
        delta=10*np.log10(y['L']/x['L'])-20*np.log10(b['rf_hz']/a['rf_hz'])
        hi=min(a['rf_hz'],b['rf_hz'])/8
        change=band(b,y,1e6,hi)['rms_fs']/band(a,x,1e6,hi)['rms_fs']-1;fr=b['rf_hz']/a['rf_hz']-1
        passed=bool(max(abs(delta))<lim['max_psd_delta_db'] and abs(change)<lim['max_relative_rms_change'] and abs(fr)<lim['max_relative_rf_change'])
        checks[label]=dict(max_absolute_psd_delta_db=float(max(abs(delta))),relative_rms_change=change,relative_rf_change=fr,passed=passed,
                           same_physical_workpoint_verified=True,frequency_grid_max_relative_difference=float(max(abs(y['f']/x['f']-1))),
                           offsets_hz=x['f'].tolist(),psd_change_db=delta.tolist())
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),cases=rows,complete=all(x['completed'] for x in rows),
             precision_checks=checks,both_full_grid_precision_passed=len(checks)==2 and all(x['passed'] for x in checks.values()),
             full_pll_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    if 'baseline_0125' in lookup and 'candidate_0125' in lookup:
        b,c=lookup['baseline_0125'],lookup['candidate_0125'];bs,cs=spectra['baseline_0125'],spectra['candidate_0125']
        assert np.allclose(bs['f'],cs['f'],rtol=1e-12,atol=0),'Different sweep grid beyond ASCII roundoff'
        hi=min(b['rf_hz'],c['rf_hz'])/8;fr=c['rf_hz']/b['rf_hz']-1
        bands=[]
        for lo in p['integration_lower_bounds_hz']:
            before,after=band(b,bs,lo,hi),band(c,cs,lo,hi)
            bands.append(dict(lower_hz=lo,upper_hz=hi,baseline=before,candidate=after,relative_rms_change=after['rms_fs']/before['rms_fs']-1))
        out.update(relative_rf_error=fr,frequency_match_passed=abs(fr)<p['frequency_match_limit'],high_offset_bands=bands,
                   frequency_grid_max_relative_difference=float(max(abs(cs['f']/bs['f']-1))),
                   offsets_hz=bs['f'].tolist(),timing_psd_change_db=(10*np.log10(cs['L']/bs['L'])-20*np.log10(c['rf_hz']/b['rf_hz'])).tolist())
    (H/'results/vco_matched_dense_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['cases','offsets_hz','timing_psd_change_db']},indent=2))

if __name__=='__main__':main()
