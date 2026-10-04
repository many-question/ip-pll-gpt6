"""Four fresh-PSS isolated noise-on checks of the measured MT560 candidate."""
from pathlib import Path
import datetime,hashlib,json,re
from noise_utils import devices

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
GROUPS=dict(tail_bias=['XV.XL.MT','XV.XL.MR','XV.XL.RREF','XV.XL.RF']+
    [f'XV.XL.M{x}{i}' for x in ['A','E'] for i in range(3,8)],
    cross_pair=['XV.XL.MN0','XV.XL.MN1'],inductor=['XV.XL.XP','XV.XL.XN'],
    cap_bank=['XV.XBP','XV.XBN','XV.CVP','XV.CVN'])

def main():
    proof=H/'results/vco_tail_band_validation.json';v=json.loads(proof.read_text())
    assert v['physical_and_numerical_comparison_verified'] and v['candidate']['periodic_passed']
    src=R/'vcotailband01/vco_tail560_band_finer_tt';pnoise=src/(src.name+'.raw')/'pn.pm.pnoise'
    d=devices(pnoise,len(v['offsets_hz']));assigned={g:[] for g in GROUPS}
    for name,value in d.items():
        if not any(value>0):continue
        hit=[g for g,inst in GROUPS.items() if any(name==x or name.startswith(x+'.') for x in inst)]
        assert len(hit)==1,('Missing or duplicate noise source',name,hit)
        assigned[hit[0]].append(name)
    source=H/'tb'/(src.name+'.scs');body=source.read_text()
    assert 'noiseon_inst=[XV] noiseon_type=all' in body and 'start=10k stop=492M dec=20' in body
    rows=[]
    for group,instances in GROUPS.items():
        case=f'vco_tail560_only_{group}_tt';dst=H/'tb'/(case+'.scs');assert not dst.exists()
        s=body.replace('noiseon_inst=[XV]','noiseon_inst=['+' '.join(instances)+']')
        s=s.replace('start=10k stop=492M dec=20','values=[1M 10M 100M]')
        dst.write_text(s,encoding='utf-8',newline='\n');rows.append(dict(group=group,run='vcotailaudit01',case=case,tb_sha256=sha(dst)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,group_instances=GROUPS,
        positive_sources=assigned,source_validation_sha256=sha(proof),source_validation=proof.name,
        source_run='vcotailband01',source_case=src.name,source_tb_sha256=sha(source),condition=v['condition'],
        offsets_hz=[1e6,1e7,1e8],limits=dict(max_relative_rf_change=1e-5,max_group_psd_difference_db=.1,max_closure_relative_error=1e-3),
        main_dut_modified=False,full_pll_acceptance=False,
        limitations=['Three noise offsets only, no RMS integral.',
                    'All cases recompute PSS. No readpss noise reuse.',
                    'Free VCO with static reference and fixed M4 chain, not the locked PLL or active sampler.',
                    'This validates attribution at the candidate operating point. It does not cure the prior frequency-match failure against CF40.'])
    dst=H/'results/vco_tail_noise_audit_protocol.json';assert not dst.exists();dst.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
