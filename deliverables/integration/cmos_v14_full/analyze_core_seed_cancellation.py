"""Audit a deliberate stop after one PSS norm, distinct from convergence failure."""
from pathlib import Path
import hashlib,json,re

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
J=ROOT/'research/runs/spectre_cmos_v14_full/coretripnoise01/core_pulsetrip_noise_probe_tt'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()

rec=json.loads((J/'result.json').read_text())
stop=json.loads((J/'cancellation.json').read_text())
log=(J/'spectre.out').read_text(errors='replace')
proof=H/'results/core_seed_probe_validation.json'
assert rec['remote_inputs_match'] and stop['stopped'] and stop['signal']=='SIGINT'
norms=re.findall(r'^Conv norm = .*$',log,re.M)
assert len(norms)==1
stoppos=log.index('ERROR (SPECTRE-25)');fatalpos=log.index('FATAL (SPECTRE-18)')
raw=J/(J.name+'.raw')/'pss.tran.pss'
out=dict(scope=__doc__,source_result=(J/'result.json').relative_to(ROOT).as_posix(),
    source_sha256=sha(J/'result.json'),cancellation=stop,shooting_norms=norms,
    log_sha256=sha(J/'spectre.out'),returned_status=rec['ok'],returncode=rec['metadata']['returncode'],
    fatal_after_stop=fatalpos>stoppos,pss_convergence_failure_established=False,
    valid_periodic_state=False,pnoise_completed=False,
    recovered_tstab=dict(path=raw.relative_to(ROOT).as_posix(),bytes=raw.stat().st_size,sha256=sha(raw)),
    controlled_followup=dict(evidence=proof.relative_to(ROOT).as_posix(),sha256=sha(proof),
        initialization_artifact_removed=json.loads(proof.read_text())['initialization_artifact_removed']),
    interpretation='Stopped after first norm to isolate missing supply IC entries. The subsequent SPECTRE-18 followed the explicit SIGINT. This is not proof that the physical candidate cannot converge. Three-node A/B removes the initial artifact; corrected PSS is a separate pending experiment.',
    full_pll_acceptance=False)
(H/'results/core_seed_cancellation_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['cancellation','recovered_tstab']},indent=2))
