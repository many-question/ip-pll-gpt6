"""Check the W80 actual-MOS probe, preserving any carrier/operating-point shift."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_vco_bias_band import read
from noise_utils import parse,selected_device_components
from build_vco_cross_width_probe import OBS

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(s):
    s=s.replace(' core_w=80u','').replace('values=[1M 10M 100M]','start=10k stop=492M dec=20')
    s=s.replace('\nsave '+' '.join(OBS)+'\n','').strip()
    return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)

def main():
    pp=H/'results/vco_cross_width_protocol.json'
    if not pp.exists():print('Cross-pair width protocol pending');return
    p=json.loads(pp.read_text());assert sha(H/'results'/p['source_validation'])==p['source_validation_sha256']
    j=R/p['run']/p['case'];src=R/p['source_run']/p['source_case'];rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Cross-pair width result pending');return
    r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
    out=dict(scope=__doc__,condition=p['condition'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
             protocol_sha256=sha(pp),completed=True,simulation_passed=bool(r['ok'] and 'spectre completes with 0 errors' in log),
             main_dut_modified=False,full_pll_acceptance=False,integrated_jitter_fs=None,limitations=p['limitations'])
    if out['simulation_passed']:
        old=json.loads((src/'result.json').read_text());dep=lambda r,n:{k:v for k,v in r['inputs_sha256'].items() if k!=n+'.scs'}
        assert dep(r,j.name)==dep(old,src.name) and not r.get('periodic_state')
        assert canonical((j/'inputs'/(j.name+'.scs')).read_text())==canonical((src/'inputs'/(src.name+'.scs')).read_text())
        b,bs=read(src);n,ns=read(j,min_points=3,expected_span_hz=(p['offsets_hz'][0],p['offsets_hz'][-1]));assert len(ns['f'])==3 and np.allclose(ns['f'],p['offsets_hz'],rtol=1e-9,atol=0)
        ix=[int(np.argmin(abs(bs['f']/f-1))) for f in ns['f']];assert np.allclose(bs['f'][ix],ns['f'],rtol=1e-9,atol=0)
        scale=lambda row:2/(2*np.pi*row['rf_hz'])**2
        stb=bs['L'][ix]*scale(b);stn=ns['L']*scale(n);fr=n['rf_hz']/b['rf_hz']-1
        op=[]
        for job,row in [(src,b),(j,n)]:
            raw=job/(job.name+'.raw');td=parse(raw/'pss.td.pss');t=td['time'];T=t[-1]-t[0];mean=lambda y:float(np.trapezoid(y,t)/T)
            item=dict(rf_hz=row['rf_hz'],carrier_peak_v=row['rf_carrier_peak_v'],vco_supply_current_a=-mean(td['VVCO:p']),
                      tail_range_v=[float(min(td['XV.XL.tail'])),float(max(td['XV.XL.tail']))])
            if all(x in td for x in OBS):
                item['mean_saved_terminal_current_a']={k:mean(td[k]) for k in OBS}
                item['rms_saved_terminal_current_a']={k:float(np.sqrt(mean(td[k]**2))) for k in OBS}
            op.append(item)
        out.update(physical_change_verified=True,baseline=b,candidate=n,operating_points=op,relative_rf_change=fr,
            carrier_match_passed=abs(fr)<p['engineering_equal_carrier_limit'],
            relative_carrier_peak_change=op[1]['carrier_peak_v']/op[0]['carrier_peak_v']-1,
            relative_supply_current_change=op[1]['vco_supply_current_a']/op[0]['vco_supply_current_a']-1,
            timing_psd_change_db=(10*np.log10(stn/stb)).tolist(),offsets_hz=ns['f'].tolist(),
            group_timing_psd_change_db={g:(10*np.log10(ns['groups'][g]/bs['groups'][g][ix]*(b['rf_hz']/n['rf_hz'])**2)).tolist() for g in bs['groups']})
        npth=j/(j.name+'.raw')/'pn.pm.pnoise';parts=selected_device_components(npth,['XV.XL.MT','XV.XL.MN0','XV.XL.MN1'],3)
        factor=scale(n)/(n['rf_carrier_peak_v']**2/2)
        out['candidate_component_timing_psd_s2_per_hz']={dev:{k:(x*factor).tolist() for k,x in d.items() if k in ['id','fn','total']} for dev,d in parts.items()}
    dest=H/'results/vco_cross_width_validation.json';dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['baseline','candidate','candidate_component_timing_psd_s2_per_hz']},indent=2))

if __name__=='__main__':main()
