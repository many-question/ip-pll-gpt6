"""Audit the stopped boundary-only PSS trial against its unchanged late-seed source."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
j=R/'coretripquiet01/core_pulsetrip_quiet_noise_tt';base=R/'coretriplate01/core_pulsetrip_late_noise_tt'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rp=j/'result.json'
if not rp.exists():print('pending collection');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('pending final hashes');raise SystemExit(0)
old=json.loads((base/'result.json').read_text());assert r['remote_inputs_match'] and not r['ok']
def canonical(s):
    s=re.sub(r'/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/coretrip(?:quiet|late)01_core_pulsetrip_(?:quiet|late)_noise_tt','__JOB__',s)
    return re.sub(r'\btstab=\S+','tstab=__ONLY_CHANGE__',s)
assert canonical((j/'inputs'/(j.name+'.scs')).read_text())==canonical((base/'inputs'/(base.name+'.scs')).read_text())
assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}=={k:v for k,v in old['inputs_sha256'].items() if k!=base.name+'.scs'}
log=(j/'spectre.out').read_text();assert sha(j/'spectre.out')==r['local_outputs_sha256']['spectre.out']
hist=re.findall(r'^Conv norm.*$',log,re.M);assert len(hist)>=5 and 'SPECTRE-25' in log
raw=j/(j.name+'.raw');path=raw/'pss.tran.pss';digest=hashlib.sha256()
with path.open('rb') as f:
    while chunk:=f.read(1024*1024):digest.update(chunk)
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
    only_tstab_changed=True,old_tstab_s=1e-6,new_tstab_s=1.134023e-6,
    convergence_history=hist,cancellation=json.loads((j/'cancellation.json').read_text()),
    raw_tstab=dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=digest.hexdigest()),
    periodic_state_valid=False,pnoise_ran=bool(list(raw.glob('*.pnoise'))),
    segmentation_fault_after_stop='SPECTRE-18' in log and log.index('SPECTRE-18')>log.index('SPECTRE-25'),
    interpretation='Changing only the shooting boundary did not establish convergence: five completed residuals7.68M/262k/335k/1.17M/4.87M. The last three rise consecutively. Deliberately stopped before maximum iterations; this is not proof no periodic solution exists.',
    next='Review short method/mesh controls before another long PSS. CF40 own-state warm settling separately uses the released long slot; not a solver substitute or accepted noise result.',
    full_pll_acceptance=False)
assert 'The steady-state solution was achieved' not in log and not out['pnoise_ran']
(H/'results/core_quiet_trial_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
