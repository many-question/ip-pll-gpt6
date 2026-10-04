"""Check a measured frontend PAC gain against its independent static phase sweep."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement
from noise_utils import parse

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],default=2)
    choice=ap.add_mutually_exclusive_group();choice.add_argument('--reference-candidate',action='store_true')
    choice.add_argument('--cp-variant',choices=['fasttail','mid70']);args=ap.parse_args()
    assert args.reference_candidate or args.cp_variant or args.round==2
    prefix=f'cp_{args.cp_variant}_phase_transfer_r{args.round}' if args.cp_variant else (
        f'reference_frontend_phase_transfer_r{args.round}' if args.reference_candidate else 'frontend_phase_transfer')
    pp=H/'results'/(prefix+'_protocol.json');p=json.loads(pp.read_text())
    assert sha(H/'results'/p['source_validation'])==p['source_validation_sha256']
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case']
    row=measurement(j,p['phase_deg'])
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],periodic=row,
             transfer_valid=False,noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    if row['completed']:
        r=json.loads((j/'result.json').read_text());src=ROOT/p['source_result']
        assert sha(src)==p['source_sha256'] and not r.get('periodic_state')
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}==p['dependencies_sha256']
        body=(j/'inputs'/(j.name+'.scs')).read_text()
        body=re.sub(r'^(VPH |save phi |pa pac ).*\n','',body,flags=re.M)
        body=body.replace('tank_replay_pm_v14','tank_replay_phase_v14').replace('XRF (vp vn phi 0)','XRF (vp vn 0)')
        assert normal(body)==normal((src.parent/'inputs'/(src.parent.name+'.scs')).read_text())
    if row.get('periodic_passed'):
        k=p['signed_static_gain_a_per_rf_rad'];residual=abs(row['mean_clamp_current_a']/k)
        balanced=bool(residual<p['balanced_phase_limit_rad'] and row['amplitude_good_fraction']>.999 and row['phase_good_fraction']>.999)
        out.update(balanced_center_verified=balanced,linearized_residual_phase_rad=residual)
        if balanced:
            raw=j/(j.name+'.raw');parent=raw/'pa.pac';signal=raw/'pa.0.pac'
            assert set(x.name for x in raw.glob('*.pac'))=={'pa.pac','pa.0.pac'}
            assert np.array_equal(parse(parent)['harmonic'],[0.])
            header=signal.read_text().split('\nTYPE\n',1)[0]
            assert all(item in header for item in ['"harmonic" 0','"freqaxis" "in"','"operating point producer" "pss"'])
            d=parse(signal);f=np.asarray(d['freq']);phi=np.asarray(d['phi']);y=np.asarray(d['VO:p'])
            assert np.allclose(f,p['offsets_hz'],rtol=1e-9,atol=0) and np.all(np.isfinite(y))
            assert np.allclose(phi,1,rtol=1e-9,atol=1e-12)
            g=y/phi;error=float(abs(g[0]/k-1));passed=error<p['low_frequency_relative_complex_error_limit']
            out.update(transfer_valid=bool(passed),pac_sha256=sha(signal),pac_parent_sha256=sha(parent),offsets_hz=f.tolist(),
                       signed_static_gain_a_per_rf_rad=k,gain_real_a_per_rad=g.real.tolist(),gain_imag_a_per_rad=g.imag.tolist(),
                       magnitude_a_per_rad=abs(g).tolist(),magnitude_relative_static_db=(20*np.log10(abs(g/k))).tolist(),
                       phase_relative_static_deg=np.angle(g/k,deg=True).tolist(),low_frequency_complex_relative_error=error,
                       low_frequency_gain_check_passed=bool(passed),physical_source_verified=True)
    (H/'results'/(prefix+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
