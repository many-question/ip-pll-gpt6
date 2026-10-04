"""Fresh-PSS sparse numerical checks for both CF40 and the MT560 candidate.

This checks the existing 100 ppm carrier/.1 dB sampled-noise limits; six
offsets cannot certify an entire noise integral. No physical circuit changes.
"""
from pathlib import Path
import datetime,hashlib,json

H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    rows=[]
    for variant,source,run in [('cf40','vco_band_cf40_finer_tt','vcobiasband01'),
                                ('tail560','vco_tail560_band_finer_tt','vcotailband01')]:
        src=H/'tb'/(source+'.scs');s=src.read_text()
        assert 'maxstep=0.25p' in s and 'maxsideband=511' in s
        assert s.count('start=10k stop=492M dec=20')==1
        body=s.replace('maxstep=0.25p','maxstep=0.125p').replace('maxsideband=511','maxsideband=1023')
        body=body.replace('start=10k stop=492M dec=20','values=[10k 100k 1M 10M 100M 492M]')
        case=f'vco_{variant}_refined_probe_tt';dst=H/'tb'/(case+'.scs')
        assert not dst.exists();dst.write_text(body,encoding='utf-8',newline='\n')
        rows.append(dict(variant=variant,case=case,run='vcorefine01',source_run=run,source_case=source,
                         source_tb_sha256=sha(src),tb_sha256=sha(dst)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
           condition='TT27/1.2V/Q5 RLC/static reference/fixed M4/10fF/only XV noise; CF40 c23 ctrl.679V and MT560 c21 ctrl.74116905779740294V.',
           fresh_pss=True,numerical_changes=dict(maxstep_s=[.25e-12,.125e-12],colored_sidebands=[511,1023]),
           limits=dict(relative_rf_change=1e-4,max_absolute_timing_psd_change_db=.1),
           main_dut_modified=False,full_pll_acceptance=False,
           limitations=['Six offsets only; no RMS or full-grid precision acceptance.',
                        'Two operating points retain their previous controls; matching must be rechecked.',
                        'Free VCO below its line width is not a valid locked PLL jitter spectrum.',
                        'No active sampler, complete programmable output chain, or full PLL PVT.'])
    dst=H/'results/vco_refinement_probe_protocol.json';assert not dst.exists()
    dst.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
