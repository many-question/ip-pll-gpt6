"""One physical cross-pair width experiment at unchanged external controls.

This first probe diagnoses direction and operating-point displacement. It is
not an equal-frequency performance claim or a proposed main-DUT replacement.
"""
from pathlib import Path
import datetime,hashlib,json

H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OBS=['XV.XL.MN0:d','XV.XL.MN1:d','XV.XL.MT:d']

def main():
    proof=H/'results/vco_tail_band_validation.json';v=json.loads(proof.read_text())
    assert v['physical_and_numerical_comparison_verified'] and v['candidate']['periodic_passed']
    audit=json.loads((H/'results/vco_tail_noise_audit_validation.json').read_text())
    cross=next(x for x in audit['cases'] if x['group']=='cross_pair');assert cross['passed']
    assert sha(ROOT/cross['source_result'])==cross['source_sha256']
    wrapper=B/'lc_vco_cf40_tail560_v14.scs';core=B/'lc_core_cf40_tail560_v14.scs'
    assert 'core_w=120u' in wrapper.read_text()
    for name in ['MN0','MN1']:
        line=next(x for x in core.read_text().splitlines() if x.startswith(name+' '))
        assert 'w=core_w l=180n' in line and 'ad=core_w*240n as=core_w*240n' in line
    source=H/'tb/vco_tail560_band_finer_tt.scs';s=source.read_text()
    line='XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vco_vdd 0) lc_vco_cf40_tail560_v14 bias_r=2500'
    assert s.count(line)==1 and 'core_w=' not in s
    s=s.replace(line,line+' core_w=80u').replace('start=10k stop=492M dec=20','values=[1M 10M 100M]')
    s+='\nsave '+' '.join(OBS)+'\n'
    case='vco_cross80_probe_tt';dst=H/'tb'/(case+'.scs');assert not dst.exists();dst.write_text(s,encoding='utf-8',newline='\n')
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='vcocross80_01',case=case,
           source_run='vcotailband01',source_case='vco_tail560_band_finer_tt',source_tb_sha256=sha(source),tb_sha256=sha(dst),
           source_validation=proof.name,source_validation_sha256=sha(proof),cross_pair_noise_audit=cross,
           physical_change=dict(cross_pair_width_um=[120,80],cross_pair_length_nm=180,geometry_diffusions_follow_width=True),
           observations=OBS,condition=v['condition']+' Cross pair W80um vs120um; controls unchanged.',
           offsets_hz=[1e6,1e7,1e8],engineering_equal_carrier_limit=1e-4,main_dut_modified=False,full_pll_acceptance=False,
           limitations=['Three offsets only, no RMS integration.',
             'External controls, coarse code, tail and bias are unchanged. Actual current, amplitude and frequency may shift.',
             'A favorable PSD at a displaced carrier is a diagnostic, not proof of a matched performance improvement.',
             'Same provisional RLC model and fixed M4 load. No active sampler or full PLL.',
             'No noise result is available merely because this testbench has been generated.'])
    dest=H/'results/vco_cross_width_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(p,indent=2))

if __name__=='__main__':main()
