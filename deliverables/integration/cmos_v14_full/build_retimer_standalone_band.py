"""Dense standalone RT4 noise and an independent numerical precision comparison."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/retimer_period_noise_validation.json';v=json.loads(proof.read_text());assert v['passed']
    pp=H/'results/retimer_period_noise_protocol.json';p=json.loads(pp.read_text())
    source=H/'tb/retimer_period_ratio1_tt.scs';body=source.read_text();body,n=re.subn(r'pn pnoise values=\[[^\]]+\]','pn pnoise start=10k stop=492M dec=20',body);assert n==1
    rows=[]
    for grade in ['fine','finer']:
        b=body
        if grade=='finer':
            b=b.replace('harms=128','harms=256').replace('maxstep=0.5p','maxstep=0.25p').replace('maxacfreq=504G','maxacfreq=1008G').replace('maxsideband=128','maxsideband=256')
        case='retimer_standalone_band_'+grade+'_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists();dest.write_text(b,encoding='utf-8',newline='\n')
        rows.append(dict(case=case,grade=grade,run='rtstandaloneband01',tb_sha256=sha(dest)))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,source_validation_sha256=sha(proof),
        source_tb_sha256=sha(source),source_protocol_sha256=sha(pp),
        condition='TT27/1.2V/actualRT4/984MHz output/10fF; noiseless ideal3.936GHzclock+984MHzdata delayed30ps,10psedges. AllRT4MOSnoiseon; freshPSSfund984MHz each.',
        integration_band_hz=[1e4,492e6],grid_points_per_decade=20,
        precision_limits=dict(max_timing_psd_delta_db=.1,max_relative_rms_change=.01),
        launch_scope='Two sequential one-thread short-slot jobs only; no auto circuit changes.',
        limitations=['Standalone ideal drive does not include noisy RF receiver/divider/LC, loading correlations or closed-loop transfer.',
            'Two numerical settings establish only this fixture precision, not PVT/MC/all33frequencies.',
            'No noise integral for an unmeasured harmonic pole is discarded: physical output fundamental984MHz lies outside10k..492MHz.'],
        full_pll_acceptance=False,main_dut_modified=False)
    for key in ['offsets_hz','comparison_limits','dispatch_failures','reason']:p.pop(key,None)
    dest=H/'results/retimer_standalone_band_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print([x['case'] for x in rows])

if __name__=='__main__':main()
