"""Measure reset-stack settling from a labelled, incomplete core tstab snapshot."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dst=ROOT/'research/diagnostics/core_counter_clear_tstab_prefix01';manifest=dst/'manifest.json';m=json.loads(manifest.read_text())
    assert not m['pss_accepted'] and not m['complete_job_result'] and m['prefix_stable_across_two_reads']
    assert sha(H/'results/core_counter_clear_noise_protocol.json')==m['protocol_sha256']
    original=dst/'original_partial.pss';view=dst/'complete_records_parser_view.pss'
    assert sha(original)==m['original_partial_sha256'] and sha(view)==m['parser_view_sha256']
    prefix=original.read_bytes()[:m['prefix_bytes']];assert hashlib.sha256(prefix).hexdigest()==m['prefix_sha256']
    assert view.read_bytes()==prefix+b'END\n'
    d=parse(view);t=d['time'];assert np.all(np.diff(t)>0) and len(t)>100 and t[0]>=3.5e-6 and t[-1]<5.25e-6
    # Exclude the first100ns after imported text-state initialization. This is
    # a stated observation window, not a claim that all fast transients settled.
    take=t>=3.6e-6;assert sum(take)>100
    nodes=[f'XP.XCOUNT.XF{i}.XF.X{stage}.XN.x' for i in range(14) for stage in ['M','S']]
    stacks={n:dict(first_v=float(d[n][0]),late_min_v=float(min(d[n][take])),late_max_v=float(max(d[n][take])),
                   last_v=float(d[n][-1])) for n in nodes}
    controls={n:dict(late_sampled_min_v=float(min(d[n][take])),late_sampled_max_v=float(max(d[n][take])),last_v=float(d[n][-1]))
              for n in ['XP.ctrl','XP.vc1','XP.XDAC.vd','XP.XDAC.b0','XP.XDAC.b3','XP.XDAC.b4']}
    out=dict(scope=__doc__,manifest=manifest.relative_to(ROOT).as_posix(),manifest_sha256=sha(manifest),
             condition='TT27/1.2V, actual LC/core with fixed slow controls, original RT/CF10/newbank and reset-clear counter; transient initialization only.',
             retained_time_range_s=[float(t[0]),float(t[-1])],late_window_s=[float(t[take][0]),float(t[-1])],
             retained_samples=len(t),late_samples=int(sum(take)),max_retained_time_gap_s=float(max(np.diff(t))),
             stacks=stacks,late_max_sampled_reset_stack_abs_v=max(max(abs(z['late_min_v']),abs(z['late_max_v'])) for z in stacks.values()),
             control_samples=controls,pss_accepted=False,random_noise_measured=False,full_pll_acceptance=False,limitations=m['limitations'])
    target=H/'results/core_clear_tstab_prefix_validation.json';assert not target.exists();target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='stacks'},indent=2))

if __name__=='__main__':main()
