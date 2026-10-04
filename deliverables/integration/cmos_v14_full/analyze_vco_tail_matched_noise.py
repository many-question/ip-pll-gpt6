"""Check actual carrier matching and six noise points for the adjusted tail."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from analyze_vco_tail_adjusted import measurement
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refine',action='store_true');args=ap.parse_args()
    label='vco_tail_matched2_noise' if args.refine else 'vco_tail_matched_noise'
    pp=H/'results'/(label+'_protocol.json')
    if not pp.exists():print('Matched-point protocol pending');return
    p=json.loads(pp.read_text());j=R/p['run']/p['case'];rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Matched-point noise pending');return
    source=R/'vcotail560_01/vco_bias_cf40_tail560_tt';sr=json.loads((source/'result.json').read_text());r=json.loads(rp.read_text())
    assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}=={k:v for k,v in sr['inputs_sha256'].items() if k!=source.name+'.scs'}
    body=(source/'inputs'/(source.name+'.scs')).read_text().replace('VB1 (b1 0) vsource dc=1.2','VB1 (b1 0) vsource dc=0').replace('VC (ctrl 0) vsource dc=0.679',f"VC (ctrl 0) vsource dc={p['proposed_control_v']:.17g}")
    normal=lambda s:re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)
    assert normal(body)==normal((j/'inputs'/(j.name+'.scs')).read_text())
    base=measurement(R/'vcocf40_01/vco_bias_cf40_tt');candidate=measurement(j)
    assert np.allclose(candidate['offsets_hz'],p['offsets_hz'],rtol=1e-9,atol=0)
    error=candidate['rf_hz']/p['target_rf_hz']-1
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),baseline=base,candidate=candidate,
        physical_change_verified=True,proposed_control_v=p['proposed_control_v'],target_rf_hz=p['target_rf_hz'],
        relative_rf_error=error,relative_rf_match_limit=p['relative_rf_match_limit'],frequency_match_passed=bool(abs(error)<p['relative_rf_match_limit']),
        timing_psd_change_db=(10*np.log10(np.array(candidate['timing_psd_s2_per_hz'])/base['timing_psd_s2_per_hz'])).tolist(),
        component_timing_psd_change_db={n:{k:(10*np.log10(np.array(x)/base['selected_noise_components_timing_psd_s2_per_hz'][n][k])).tolist() for k,x in terms.items()} for n,terms in candidate['selected_noise_components_timing_psd_s2_per_hz'].items()},
        relative_carrier_change=candidate['rf_carrier_peak_v']/base['rf_carrier_peak_v']-1,
        relative_current_change=candidate['vco_supply_power_mw']/base['vco_supply_power_mw']-1,
        integrated_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    (H/'results'/(label+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['baseline','candidate']},indent=2))

if __name__=='__main__':main()
