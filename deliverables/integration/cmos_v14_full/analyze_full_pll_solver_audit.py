"""Preserve failed hypotheses and actual tolerance/initialization evidence."""
from pathlib import Path
import collections,hashlib,json,re
import numpy as np
from transient_diagnostics import recovery,effective
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    cases=[('pllnoisesettle01','full_pll_noise_settling_tt'),('pllnoisegear01','full_pll_noise_gear_diagnosis_tt'),
        ('pllstrictdiag01','full_pll_strict_diagnostic_tt'),('pllnova01','full_pll_no_observer_tt'),
        ('pllabsoluteiab01','full_pll_absolute_iab_tt'),('pllabsolutevab01','full_pll_absolute_vab_tt'),
        ('pllcurrent100fa01','full_pll_current_100fa_tt'),('pllcurrent10fa01','full_pll_current_10fa_tt')]
    rows=[];edges={}
    for run,case in cases:
        row=dict(run=run,case=case,result_collected=False);rows.append(row);j=R/run/case;rp=j/'result.json'
        if not rp.exists():continue
        r=json.loads(rp.read_text())
        if not r.get('local_outputs_sha256'):continue
        assert r['remote_inputs_match'] and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        s=(j/'spectre.out').read_text();rec=recovery(s)
        row.update(result_collected=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
            effective=effective(s),recovery=rec,zero_terminal_errors='spectre completes with 0 errors' in s,
            log_sha256=sha(j/'spectre.out'),errors=r['errors'],
            diagnostic_solution_node_counts=dict(collections.Counter(re.findall(r'convergence failure at solution:\s*(\S+)',s))))
        cache=j/'waveforms.npz'
        if cache.exists():
            assert sha(cache)==r['local_outputs_sha256'][cache.name]
            with np.load(cache) as z:
                t=z['time'];row['time_range_s']=[float(t[0]),float(t[-1])]
                if run in ['pllabsoluteiab01','pllcurrent100fa01','pllcurrent10fa01']:
                    e=cross(t,z['out'],.6);edges[run]=e[(e>1e-9)&(e<4.8e-9)]
            row['cache_sha256']=sha(cache)
        row['short_convergence_screen_passed']=row['zero_terminal_errors'] and rec['numerically_clean']
    local_comparisons={}
    if 'pllabsoluteiab01' in edges:
        base=edges['pllabsoluteiab01']
        for name,e in edges.items():
            if name=='pllabsoluteiab01':continue
            assert len(e)==len(base) and len(e)>=3
            v=(e-base)*1e15
            local_comparisons[name]=dict(edges=len(e),maximum_absolute_difference_fs=float(max(abs(v))),
                mean_removed_rms_fs=float(np.std(v)),scope='Only1..4.8ns startup edges; not a stationary or broadband jitter floor.')
    out=dict(scope=__doc__,cases=rows,local_current_tolerance_edge_comparisons=local_comparisons,full_pll_acceptance=False,noise_measured=False,
        findings=['Changing only integration method did not remove strict noise-OFF Newton recovery.',
          'Detailed failures often named the power observer, but removing both nonfunctional VA observers did not remove recovery. That symptom did not establish the observer as the root cause.',
          'In the no-VA5ns pair, current tolerance1pA with voltage tolerance1nV was clean; voltage tolerance1uV with current tolerance1fA was not. Both used reltol1e-6/Trap/.5ps and unchanged physical DUT.',
          'The corresponding complete-PLL noise pair retains1nV/reltol1e-6 and uses1pA. This is a numerical-repair candidate; longer stability, floor and noise precision still require verification.'],
        limitations=['Printed counts may be suppressed; report them as lower bounds.','Short or intentionally stopped runs cannot qualify stationary fullPLL jitter.','100fA/10fA bracketing uses one requested thread instead of seven; it is an additional numerical screen, not a pure thread-invariant precision proof.'])
    (H/'results/full_pll_solver_audit_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
