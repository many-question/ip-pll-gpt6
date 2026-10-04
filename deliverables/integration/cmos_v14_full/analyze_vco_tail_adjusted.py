"""Compare three actual tail sizes at identical fixture settings, without RMS."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_vco_bias_band import read
from noise_utils import parse,selected_device_components
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(j):
    result={}
    for p in (j/'inputs').iterdir():
        name='TB' if p.name==j.name+'.scs' else p.name
        text=p.read_text()
        for variant in ['cf40_tail560','cf40_tail2']:
            name=name.replace(variant,'cf40');text=text.replace(variant,'cf40')
        if name=='lc_core_cf40_v14.scs':
            assert len(re.findall(r'^MT .*$',text,re.M))==1
            text=re.sub(r'^MT .*$', 'MT VERIFIED_SEPARATELY',text,flags=re.M)
        text=re.sub(r'writefinal="[^"]+"','writefinal="STATE"',text)
        result[name]=text
    return result

def measurement(j):
    row,s=read(j,min_points=6);assert len(s['f'])==6
    td=parse(j/(j.name+'.raw')/'pss.td.pss');t=td['time'];T=t[-1]-t[0]
    cp=row['rf_carrier_peak_v']**2/2;scale=2/cp/(2*np.pi*row['rf_hz'])**2
    parts=selected_device_components(j/(j.name+'.raw')/'pn.pm.pnoise',['XV.XL.MT','XV.XL.MN0','XV.XL.MN1'],6)
    row.update(vco_supply_power_mw=float(-1.2*np.trapezoid(td['VVCO:p'],t)/T*1e3),
        timing_psd_s2_per_hz=(2*s['L']/(2*np.pi*row['rf_hz'])**2).tolist(),
        selected_noise_components_timing_psd_s2_per_hz={name:{k:(x*scale).tolist() for k,x in d.items() if k in ['id','fn','total']} for name,d in parts.items()},
        node_ranges_v={n:[float(min(td[n])),float(max(td[n]))] for n in ['XV.XL.tail','XV.XL.nfilt','vp','vn']})
    return row

def main():
    pp=H/'results/vco_tail_adjusted_protocol.json';p=json.loads(pp.read_text())
    j=R/p['run']/p['case'];rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):print('Adjusted-tail candidate pending');return
    if not json.loads(rp.read_text())['ok']:print('Adjusted-tail candidate failed; inspect source log');return
    specs=[('base300','vcocf40_01','vco_bias_cf40_tt',300,1),('tail600','vcotail2_01','vco_bias_cf40_tail2_tt',600,2),('tail560',p['run'],p['case'],560,2)]
    reference=None;rows=[]
    for label,run,case,w,l in specs:
        job=R/run/case;c=canonical(job)
        if reference is None:reference=c
        assert c==reference,'Unexpected fixture or physical change'
        core=next((job/'inputs').glob('lc_core_cf40*.scs'))
        expected=f'MT (tail nfilt vss vss) nch w={w}u l={l}u ad={w}u*240n as={w}u*240n pd=2*({w}u+240n) ps=2*({w}u+240n)'
        assert core.read_text().count(expected)==1
        row=measurement(job);assert np.allclose(row['offsets_hz'],p['offsets_hz'],rtol=1e-9,atol=0)
        row.update(label=label,tail_width_um=w,tail_length_um=l);rows.append(row)
    base=rows[0]
    for row in rows[1:]:
        fr=row['rf_hz']/base['rf_hz']-1;ar=row['rf_carrier_peak_v']/base['rf_carrier_peak_v']-1
        row.update(relative_rf_change=fr,relative_carrier_change=ar,
            relative_supply_current_change=row['vco_supply_power_mw']/base['vco_supply_power_mw']-1,
            timing_psd_change_db=(10*np.log10(np.array(row['timing_psd_s2_per_hz'])/base['timing_psd_s2_per_hz'])).tolist(),
            comparable_operating_point=bool(abs(fr)<.001 and abs(ar)<.01))
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),physical_change_verified=True,cases=rows,
        complete=True,integrated_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,
        operating_point_limits=dict(relative_rf=.001,relative_carrier=.01),limitations=p['limitations'])
    (H/'results/vco_tail_adjusted_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in out.items() if k!='cases'},'cases':[{k:v for k,v in row.items() if k in ['label','rf_hz','rf_carrier_peak_v','vco_supply_power_mw','relative_rf_change','relative_carrier_change','relative_supply_current_change','timing_psd_change_db','comparable_operating_point']} for row in rows]},indent=2))

if __name__=='__main__':main()
