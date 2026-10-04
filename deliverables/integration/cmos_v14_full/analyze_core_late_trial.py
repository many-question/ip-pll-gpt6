"""Audit a deliberately stopped IC-only PSS trial, retaining its negative result."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
j=R/'coretriplate01/core_pulsetrip_late_noise_tt';base=R/'coretripsupply01/core_pulsetrip_supply_noise_tt'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rec=json.loads((j/'result.json').read_text());old=json.loads((base/'result.json').read_text())
assert rec['remote_inputs_match'] and rec.get('local_outputs_sha256') and not rec['ok']
def canonical(s):
    s=re.sub(r'/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/coretrip(?:late|supply)01_core_pulsetrip_(?:late|supply)_noise_tt','__REMOTE_JOB__',s)
    return s.replace('core_pulsetrip_late_seed_tt.ic','__SEED__').replace('core_pulsetrip_supply_seed_tt.ic','__SEED__')
assert canonical((j/'inputs'/(j.name+'.scs')).read_text())==canonical((base/'inputs'/(base.name+'.scs')).read_text())
deps=lambda r,n:{k:v for k,v in r['inputs_sha256'].items() if k not in [n+'.scs','core_pulsetrip_late_seed_tt.ic','core_pulsetrip_supply_seed_tt.ic']}
assert deps(rec,j.name)==deps(old,base.name)
protocol=json.loads((H/'results/core_late_seed_protocol.json').read_text())
assert rec['inputs_sha256']['core_pulsetrip_late_seed_tt.ic']==protocol['seed_sha256']
log=(j/'spectre.out').read_text();blog=(base/'spectre.out').read_text()
assert sha(j/'spectre.out')==rec['local_outputs_sha256']['spectre.out']
hist=re.findall(r'^Conv norm.*$',log,re.M)
assert len(hist)>=3 and 'SPECTRE-25' in log and 'The steady-state solution was achieved' not in log
raw=j/(j.name+'.raw');p=raw/'pss.tran.pss';digest=hashlib.sha256()
with p.open('rb') as f:
    while chunk:=f.read(1024*1024):digest.update(chunk)
out=dict(scope=__doc__,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'),
    only_physical_seed_changed=True,previous_convergence_history=re.findall(r'^Conv norm.*$',blog,re.M),
    convergence_history=hist,cancellation=json.loads((j/'cancellation.json').read_text()),
    raw_tstab=dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest.hexdigest()),
    pnoise_ran=bool(list(raw.glob('*.pnoise'))),periodic_state_valid=False,
    segmentation_fault_after_stop='SPECTRE-18' in log and log.index('SPECTRE-18')>log.index('SPECTRE-25'),
    interpretation='The complete recovered log contains FIVE residuals:3.71M/127k/335k/3.19M/2.34M. The initial3.71M is essentially unchanged from3.7M in the previous trial. Later physical initialization did not establish convergence; deliberate cancellation does not prove mathematical nonexistence or exhausted iterations.',
    progress_summary_correction='A24-line remote tail omitted the first3.71M residual. Earlier commentary and the preserved cancellation reason counted only the last four and incorrectly called127k the first. This complete-log audit supersedes that count and the claimed29xfirst-residual reduction.',
    next='Inspect the recovered actual initialization trajectory before selecting a single controlled follow-up. No automatic solver sweep or fullband dispatch.',
    full_pll_acceptance=False)
assert not out['pnoise_ran']
(H/'results/core_late_trial_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
