"""Evaluate stronger VCO bias from six independent fresh-PSS noise points; no RMS."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_vco_bias_band import read
from noise_utils import parse,selected_device_components
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/vco_current_protocol.json';p=json.loads(pp.read_text())
    base=R/p['source_run']/p['source_case'];candidate=R/p['run']/p['case']
    rp=candidate/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Candidate pending');return
    def settings(j):
        rec=json.loads((j/'result.json').read_text())
        return {k:v for k,v in rec['inputs_sha256'].items() if k!=j.name+'.scs'}
    assert settings(base)==settings(candidate)
    before=(base/'inputs'/(base.name+'.scs')).read_text();after=(candidate/'inputs'/(candidate.name+'.scs')).read_text()
    assert after.count('lc_vco_cf40_v14 bias_r=2000')==1
    normalize=lambda s:re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)
    assert normalize(before)==normalize(after.replace('lc_vco_cf40_v14 bias_r=2000','lc_vco_cf40_v14 bias_r=2500'))
    records=[];spec=[]
    for j in [base,candidate]:
        row,s=read(j,min_points=6);assert len(s['f'])==6 and np.allclose(s['f'],p['offsets_hz'],rtol=1e-9,atol=0)
        td=parse(j/(j.name+'.raw')/'pss.td.pss');t=td['time'];T=t[-1]-t[0]
        rawparts=selected_device_components(j/(j.name+'.raw')/'pn.pm.pnoise',['XV.XL.MT','XV.XL.MN0','XV.XL.MN1'],6)
        carrier=row['rf_carrier_peak_v']**2/2
        row['selected_noise_components_timing_psd_s2_per_hz']={name:{k:(2*x/carrier/(2*np.pi*row['rf_hz'])**2).tolist() for k,x in fields.items() if k in ['id','fn','total']} for name,fields in rawparts.items()}
        vr=lambda a:[float(np.min(a)),float(np.max(a))]
        row.update(vco_average_supply_ma=float(-np.trapezoid(td['VVCO:p'],t)/T*1e3),
            vco_average_supply_mw=float(-1.2*np.trapezoid(td['VVCO:p'],t)/T*1e3),
            node_ranges_v={k:vr(td[k]) for k in ['vp','vn','ctrl','XV.XL.tail','XV.XL.nfilt']},
            core_terminal_ranges_v=dict(MN0_vds=vr(td['vp']-td['XV.XL.tail']),MN0_vgs=vr(td['vn']-td['XV.XL.tail']),
                MN1_vds=vr(td['vn']-td['XV.XL.tail']),MN1_vgs=vr(td['vp']-td['XV.XL.tail']),
                MT_vds=vr(td['XV.XL.tail']),MT_vgs=vr(td['XV.XL.nfilt'])),
            top_device_contributors_at_1mhz=sorted([dict(device=n,fraction=float(x[2]/s['L'][2])) for n,x in s['parts'].items()],key=lambda z:-z['fraction'])[:12])
        records.append(row);spec.append(s)
    delta=10*np.log10(spec[1]['L']/spec[0]['L'])
    f0,f1=[x['rf_hz'] for x in records];timing_delta=delta-20*np.log10(f1/f0)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],physical_change_verified=True,
        baseline=records[0],candidate=records[1],ssb_pm_change_db=delta.tolist(),timing_psd_change_db=timing_delta.tolist(),
        relative_rf_frequency_change=f1/f0-1,relative_carrier_peak_change=records[1]['rf_carrier_peak_v']/records[0]['rf_carrier_peak_v']-1,
        power_change_mw=records[1]['vco_average_supply_mw']-records[0]['vco_average_supply_mw'],
        target_frequency_rematch_required=True,integrated_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,
        limitations=p['limitations']+['Terminal ranges are observations, not device-reliability signoff.'])
    (H/'results/vco_current_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['baseline','candidate']},indent=2))

if __name__=='__main__':main()
