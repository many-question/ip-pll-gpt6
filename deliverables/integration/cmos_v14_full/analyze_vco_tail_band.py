"""Compare dense, equally refined tail-candidate and CF40 reference spectra."""
from pathlib import Path
import hashlib,json
import numpy as np
from analyze_vco_bias_band import read,integral
from analyze_vco_tail_adjusted import canonical
from noise_utils import parse,selected_device_components
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/vco_tail_band_protocol.json'
    if not pp.exists():print('Dense-tail protocol pending');return
    p=json.loads(pp.read_text());j=R/p['run']/p['case'];rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Dense-tail result pending');return
    proof=H/'results/vco_tail_matched2_noise_validation.json';assert sha(proof)==p['source_validation_sha256']
    seed=json.loads(proof.read_text());base=R/p['baseline_run']/p['baseline_case']
    before=canonical(base);after=canonical(j)
    after['TB']=after['TB'].replace('VB1 (b1 0) vsource dc=0','VB1 (b1 0) vsource dc=1.2').replace(f"VC (ctrl 0) vsource dc={seed['proposed_control_v']:.17g}",'VC (ctrl 0) vsource dc=0.679')
    assert before==after,'Unexpected physical or numerical difference'
    src=R/'vcotailmatched02/vco_tail560_matched2_tt'
    dep=lambda job:{k:v for k,v in json.loads((job/'result.json').read_text())['inputs_sha256'].items() if k!=job.name+'.scs'}
    assert dep(src)==dep(j),'Changed circuit since the matched-frequency probe'
    b,bs=read(base);c,cs=read(j);assert np.allclose(bs['f'],cs['f'],rtol=1e-12,atol=0)
    hi=min(b['rf_hz'],c['rf_hz'])/8;fr=c['rf_hz']/b['rf_hz']-1;bands=[]
    for job,row,s in [(base,b,bs),(j,c,cs)]:
        raw=job/(job.name+'.raw');td=parse(raw/'pss.td.pss');t=td['time'];T=t[-1]-t[0]
        scale=2/(2*np.pi*row['rf_hz'])**2
        total=scale*integral(s['f'],s['L'],1e6,hi)
        parts=selected_device_components(raw/'pn.pm.pnoise',['XV.XL.MT','XV.XL.MN0','XV.XL.MN1'],len(s['f']))
        cp=row['rf_carrier_peak_v']**2/2
        row.update(vco_supply_power_mw=float(-1.2*np.trapezoid(td['VVCO:p'],t)/T*1e3),
            selected_component_high_band_variance_fraction={name:{k:scale/cp*integral(s['f'],value,1e6,hi)/total
                for k,value in terms.items()} for name,terms in parts.items()},
            top_devices_high_band=sorted([dict(device=name,variance_fraction=scale*integral(s['f'],value,1e6,hi)/total)
                for name,value in s['parts'].items()],key=lambda x:-x['variance_fraction'])[:12])
    for lo in [1e6,2e6,5e6,10e6,100e6]:
        values=[]
        for row,s in [(b,bs),(c,cs)]:
            scale=2/(2*np.pi*row['rf_hz'])**2;value=scale*integral(s['f'],s['L'],lo,hi)
            groups={g:scale*integral(s['f'],x,lo,hi) for g,x in s['groups'].items()};assert abs(sum(groups.values())/value-1)<1e-9
            values.append(dict(rms_fs=float(np.sqrt(value)*1e15),powerlaw_rms_fs=float(np.sqrt(scale*integral(s['f'],s['L'],lo,hi,True))*1e15),
                group_variance_fraction={g:x/value for g,x in groups.items()}))
        bands.append(dict(lower_hz=lo,upper_hz=hi,baseline=values[0],candidate=values[1],relative_rms_change=values[1]['rms_fs']/values[0]['rms_fs']-1))
    delta=10*np.log10(cs['L']/bs['L'])-20*np.log10(c['rf_hz']/b['rf_hz'])
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),baseline=b,candidate=c,
        physical_and_numerical_comparison_verified=True,relative_rf_change=fr,frequency_match_limit=1e-4,
        frequency_match_passed=bool(abs(fr)<1e-4),offsets_hz=cs['f'].tolist(),timing_psd_change_db=delta.tolist(),high_offset_bands=bands,
        relative_vco_supply_current_change=c['vco_supply_power_mw']/b['vco_supply_power_mw']-1,
        relative_rf_carrier_amplitude_change=c['rf_carrier_peak_v']/b['rf_carrier_peak_v']-1,
        independent_candidate_precision_passed=False,full_pll_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    (H/'results/vco_tail_band_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['baseline','candidate','offsets_hz','timing_psd_change_db']},indent=2))

if __name__=='__main__':main()
