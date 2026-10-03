"""Record the deliberately stopped, tighter-itres comparison with its input proof."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
j=R/'coretriplinear01/core_pulsetrip_linear_noise_tt';base=R/'coretripsupply01/core_pulsetrip_supply_noise_tt'
rec=json.loads((j/'result.json').read_text());old=json.loads((base/'result.json').read_text())
assert rec['remote_inputs_match'] and rec.get('local_outputs_sha256') and not rec['ok']
tb=(j/'inputs'/(j.name+'.scs')).read_text();bt=(base/'inputs'/(base.name+'.scs')).read_text()
# The runner expands output and include paths to each separate remote UUID.
def canonical(s):
    for prefix in ['coretriplinear01_core_pulsetrip_linear_noise_tt','coretripsupply01_core_pulsetrip_supply_noise_tt']:
        s=s.replace('/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/'+prefix,'__REMOTE_JOB__')
    return s
assert canonical(tb.replace(' itres=1e-6',''))==canonical(bt)
assert {k:v for k,v in rec['inputs_sha256'].items() if k!=j.name+'.scs'}=={k:v for k,v in old['inputs_sha256'].items() if k!=base.name+'.scs'}
log=(j/'spectre.out').read_text();blog=(base/'spectre.out').read_text()
hist=re.findall(r'^Conv norm.*$',log,re.M);before=re.findall(r'^Conv norm.*$',blog,re.M)
assert len(hist)==4 and 'SPECTRE-25' in log and 'pss: The steady-state solution was achieved' not in log
raw=j/(j.name+'.raw');p=raw/'pss.tran.pss';digest=hashlib.sha256()
with p.open('rb') as f:
    while chunk:=f.read(1024*1024):digest.update(chunk)
out=dict(scope=__doc__,source_result=(j/'result.json').relative_to(ROOT).as_posix(),
    source_sha256=hashlib.sha256((j/'result.json').read_bytes()).hexdigest(),
    only_itres_changed=True,previous_convergence_history=before,convergence_history=hist,
    cancellation=json.loads((j/'cancellation.json').read_text()),
    raw_tstab=dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest.hexdigest()),
    pnoise_ran=bool(list(raw.glob('*.pnoise'))),periodic_state_valid=False,
    segmentation_fault_after_stop='SPECTRE-18' in log and log.index('SPECTRE-18')>log.index('SPECTRE-25'),
    interpretation='The first three printed norms remain3.7M,75.3k,340k; fourth1.23M vs2.1M prior. Tighter linear residual did not restore contraction in the observed four iterations. Deliberately stopped; no claim of mathematical nonexistence or exhausting maximum iterations.',
    next='Six-thread slot reassigned to four physical near-lock candidate comparisons; no automatic further PSS retry or fullband run.',
    full_pll_acceptance=False)
assert not out['pnoise_ran']
(H/'results/core_linear_trial_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
