"""Validate a fresh measured carrier match and six actual-device noise points."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_vco_tail_adjusted import measurement
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(s):
    s=re.sub(r'^VC \(ctrl 0\) vsource dc=\S+','VC (ctrl 0) vsource dc=CONTROL',s,flags=re.M)
    return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)

def main():
    pp=H/'results/vco_tail_refined_match_protocol.json'
    if not pp.exists():print('Refined carrier-match protocol pending');return
    p=json.loads(pp.read_text());assert sha(H/'results'/p['source_validation'])==p['source_validation_sha256']
    j=R/p['run']/p['case'];rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Refined carrier-match result pending');return
    r=json.loads(rp.read_text());src=R/p['source_run']/p['source_case'];base=R/p['source_run']/p['baseline_case']
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
             completed=True,simulation_passed=r['ok'],main_dut_modified=False,full_pll_acceptance=False,integrated_jitter_fs=None,limitations=p['limitations'])
    if r['ok']:
        old=json.loads((src/'result.json').read_text());dep=lambda r,n:{k:v for k,v in r['inputs_sha256'].items() if k!=n+'.scs'}
        assert dep(r,j.name)==dep(old,src.name)
        assert canonical((j/'inputs'/(j.name+'.scs')).read_text())==canonical((src/'inputs'/(src.name+'.scs')).read_text())
        b=measurement(base);n=measurement(j);assert abs(b['rf_hz']/p['target_rf_hz']-1)<1e-12
        fr=n['rf_hz']/b['rf_hz']-1
        out.update(physical_control_change_verified=True,baseline=b,candidate=n,proposed_control_v=p['proposed_control_v'],
             relative_rf_error=fr,frequency_match_passed=abs(fr)<p['relative_rf_match_limit'],
             timing_psd_change_db=(10*np.log10(np.array(n['timing_psd_s2_per_hz'])/b['timing_psd_s2_per_hz'])).tolist(),
             relative_carrier_change=n['rf_carrier_peak_v']/b['rf_carrier_peak_v']-1,
             relative_supply_current_change=n['vco_supply_power_mw']/b['vco_supply_power_mw']-1)
    (H/'results/vco_tail_refined_match_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['baseline','candidate']},indent=2))

if __name__=='__main__':main()
