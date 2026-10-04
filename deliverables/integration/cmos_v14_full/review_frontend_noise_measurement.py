"""Join completed frontend noise points to measured PAC gain without integration."""
from pathlib import Path
import hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    npth=H/'results/frontend_noise_r2_all_validation.json';apth=H/'results/frontend_phase_transfer_validation.json'
    n=json.loads(npth.read_text());a=json.loads(apth.read_text())
    assert n['noise_valid'] and a['transfer_valid']
    assert n['condition']==a['condition'] and n['periodic']['phase_deg']==a['periodic']['phase_deg']
    nr=ROOT/n['periodic']['source_result'];ar=ROOT/a['periodic']['source_result']
    assert sha(nr)==n['periodic']['source_sha256'] and sha(ar)==a['periodic']['source_sha256']
    raw=nr.parent/(nr.parent.name+'.raw')
    prefix=ROOT/'research/diagnostics/frontend_noise2all_first_point01/manifest.json';m=json.loads(prefix.read_text())
    assert hashlib.sha256((raw/'pn.pnoise').read_bytes()[:m['prefix_bytes']]).hexdigest()==m['prefix_sha256']
    snapshot=ROOT/'research/diagnostics/frontend_noise2all_pss_snapshot01/manifest.json';s=json.loads(snapshot.read_text())
    assert all(sha(raw/k)==v['sha256'] for k,v in s['files'].items())
    rows=[];frf=3.936e9
    for i,f in enumerate(n['offsets_hz']):
        index=[k for k,x in enumerate(a['offsets_hz']) if abs(f/x-1)<1e-12];assert len(index)==1;k=index[0]
        gain=a['magnitude_a_per_rad'][k];phase=n['current_psd_a2_per_hz'][i]/gain**2
        rows.append(dict(offset_hz=f,current_asd_a_per_sqrt_hz=n['current_asd_a_per_sqrt_hz'][i],
                         gain_magnitude_a_per_rf_rad=gain,gain_phase_relative_static_deg=a['phase_relative_static_deg'][k],
                         input_equivalent_rf_phase_psd_rad2_per_hz=phase,
                         input_equivalent_timing_asd_fs_per_sqrt_hz=float(np.sqrt(phase)/(2*np.pi*frf)*1e15),
                         group_variance_fraction={g:v[i] for g,v in n['group_variance_fraction'].items()}))
    out=dict(scope=__doc__,noise_validation_sha256=sha(npth),pac_validation_sha256=sha(apth),condition=n['condition'],
             rf_hz=frf,phase_deg=n['periodic']['phase_deg'],points=rows,
             accepted_pss_snapshot_confirmed=True,first_noise_point_snapshot_confirmed=True,
             snapshot_manifest_sha256=sha(snapshot),first_point_manifest_sha256=sha(prefix),
             integrated_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,
             limitations=['Inputreferral uses the measured sideband0 current response at each exact frequency, no interpolation.',
                          'This input-equivalent noise is not the closed-loop outputnoise; loopfilter,VCO,coupling and FLL dynamics are absent.',
                          'Three points cannot establish an integrated noise budget or the band-integrated dominant group.',
                          'Fresh per-group noise-on and numerical/PVT checks remain necessary.'])
    dst=H/'results/frontend_noise_measurement_review.json';assert not dst.exists();dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
