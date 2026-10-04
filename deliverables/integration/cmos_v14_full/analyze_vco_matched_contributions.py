"""Account for the measured six-point timing-PSD change at matched RF carriers.

This is an exact partition of existing all-noise Spectre device contributions,
not a new noise-on isolation run or an integrated jitter measurement.
"""
from pathlib import Path
import hashlib,json
import numpy as np

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source=H/'results/vco_tail_refined_match_validation.json';v=json.loads(source.read_text())
    assert v['completed'] and v['frequency_match_passed']
    b,c=v['baseline'],v['candidate']
    for x in [b,c]:assert sha(ROOT/x['source_result'])==x['source_sha256']
    f=np.array(b['offsets_hz']);assert np.allclose(f,c['offsets_hz'],rtol=1e-12,atol=0)
    before=np.array(b['timing_psd_s2_per_hz']);after=np.array(c['timing_psd_s2_per_hz'])
    delta=after-before;assert np.all(delta<0)
    groups={}
    for side,x in [('baseline',b),('candidate',c)]:
        d=x['selected_noise_components_timing_psd_s2_per_hz']
        mt=np.array(d['XV.XL.MT']['total'])
        cross=sum(np.array(d[n]['total']) for n in ['XV.XL.MN0','XV.XL.MN1'])
        rest=np.array(x['timing_psd_s2_per_hz'])-mt-cross;assert np.all(rest>=0)
        groups[side]=dict(tail_transistor=mt,cross_pair=cross,other=rest)
    rows=[]
    for i,hz in enumerate(f):
        parts={n:dict(baseline_psd=float(groups['baseline'][n][i]),candidate_psd=float(groups['candidate'][n][i]),
                      candidate_variance_fraction=float(groups['candidate'][n][i]/after[i]),
                      fraction_of_total_reduction=float((groups['baseline'][n][i]-groups['candidate'][n][i])/-delta[i]))
               for n in groups['baseline']}
        assert abs(sum(x['fraction_of_total_reduction'] for x in parts.values())-1)<1e-12
        components={}
        for term in ['fn','id','total']:
            old=b['selected_noise_components_timing_psd_s2_per_hz']['XV.XL.MT'][term][i]
            new=c['selected_noise_components_timing_psd_s2_per_hz']['XV.XL.MT'][term][i]
            components[term]=dict(ratio=new/old,change_db=float(10*np.log10(new/old)))
        rows.append(dict(offset_hz=float(hz),total_change_db=float(10*np.log10(after[i]/before[i])),groups=parts,tail_components=components))
    out=dict(scope=__doc__,source_validation=source.name,source_validation_sha256=sha(source),condition=v['condition'],
             carrier_relative_difference=v['relative_rf_error'],frequency_match_passed=True,points=rows,
             noise_on_isolation_at_this_workpoint=False,integrated_jitter_fs=None,main_dut_modified=False,full_pll_acceptance=False,
             limitations=['All-noise decomposition at the newmatched workpoint. Earlier independent noise-on audit used a different control voltage.',
                          'Transistor dimensions, coarsecode, control, carrier amplitude and current all differ; not a pure area effect.',
                          'Other contains the coil, capacitorbank and remaining bias noise, not an identified single device.',
                          'Low-offset freeoscillator points do not supply locked-PLL jitter; no sparse integration.'])
    dest=H/'results/vco_matched_contributions.json';assert not dest.exists()
    dest.write_text(json.dumps(out,indent=2)+'\n')
    for row in rows:
        if row['offset_hz']>=1e6:
            print(json.dumps(row))

if __name__=='__main__':main()
