"""Compare baseline standalone edge noise with full-frontend reference attribution.

Different load models are intentionally compared to assess a screening fixture.
Agreement is reported at measured points, not used as a fullPLL acceptance gate.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,header
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    v=json.loads((H/'results/reference_buffer_noise_validation.json').read_text())
    b=next(x for x in v['cases'] if x['variant']=='baseline');assert b.get('noise_valid')
    nr=H/'results/frontend_noise_r2_all_validation.json';ar=H/'results/frontend_phase_transfer_validation.json'
    n=json.loads(nr.read_text());a=json.loads(ar.read_text());assert n['noise_valid'] and a['transfer_valid']
    rp=ROOT/b['source_result'];assert sha(rp)==b['source_sha256']
    raw=rp.parent/(rp.parent.name+'.raw')/'pnMedge.0.sample.pnoise';assert sha(raw)==b['noise_sha256']
    data=parse(raw);f=data['freq'];st=data['out']**2/header(raw,'slew rate event_1')**2
    assert np.allclose(st,b['timing_psd_s2_per_hz'],rtol=1e-12,atol=0)
    rows=[]
    for i,hz in enumerate(n['offsets_hz']):
        ix=np.flatnonzero(abs(f/hz-1)<1e-9);assert len(ix)==1
        ai=[k for k,x in enumerate(a['offsets_hz']) if abs(x/hz-1)<1e-9];assert len(ai)==1
        full=n['group_psd_a2_per_hz']['reference'][i]/a['magnitude_a_per_rad'][ai[0]]**2/(2*np.pi*3.936e9)**2
        standalone=float(st[ix[0]])
        rows.append(dict(offset_hz=hz,standalone_timing_psd_s2_per_hz=standalone,
                         frontend_input_equivalent_reference_timing_psd_s2_per_hz=full,
                         standalone_vs_frontend_db=float(10*np.log10(standalone/full))))
    out=dict(scope=__doc__,baseline_analysis_snapshot=b,baseline_condition=v['condition'],
             frontend_condition=n['condition'],noise_validation_sha256=sha(nr),pac_validation_sha256=sha(ar),
             points=rows,independent_frontend_noise_on_verified=False,full_pll_acceptance=False,
             limitations=['Standalone uses2pF lumpedload; frontend has1.9pFcontrolapproximation plus actual sampler/pulser/detector load and RFbackaction.',
                          'Fullfrontend value is referred by measured RF-phase-to-current PAC gain; this is an equivalent aperturetiming quantity.',
                          'Three points test fixture representativeness, not exact equivalence or integration of a compositePLL budget.',
                          'Reference-only fresh-PSS isolation and numerical precision checks are still running or pending.'])
    dst=H/'results/reference_frontend_baseline_comparison.json';assert not dst.exists();dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
