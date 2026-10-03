"""Prepare a one-parameter shooting linear-solver diagnostic, not a launched retry.

Spectre21.1 pss help states that itres controls the iterative linear equation
residual at each Newton iteration; tightening can improve Newton convergence
without relaxing the final circuit accuracy. This is a hypothesis to test only
after reviewing the current supply-corrected run, not proof of its root cause.
"""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
helpfile=ROOT/'research/spectre_help/pss.txt';helptext=helpfile.read_text()
assert 'Default value for' in helptext and 'shooting APS flow is 1e-3' in helptext
source=H/'tb/core_pulsetrip_supply_noise_tt.scs';body=source.read_text()
assert 'itres=' not in body and body.count('maxperiods=10')==1
body=body.replace('maxperiods=10','maxperiods=10 itres=1e-6')
dest=H/'tb/core_pulsetrip_linear_noise_tt.scs';assert not dest.exists();dest.write_text(body)
assert body.replace(' itres=1e-6','')==source.read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=dict(scope=__doc__,status='prepared_not_run',run='coretriplinear01',case=dest.stem,
    source_tb_sha256=sha(source),candidate_tb_sha256=sha(dest),local_help_sha256=sha(helpfile),
    change='Only set PSS itres=1e-6. Identicalphysicalcore,correctedIC,timing,saves,method,maxstep,reltol,abstol,steadyratioand10iterations.',
    default_evidence='LocalSpectre21.1 pss help: default shooting APS itres1e-3. This default is documented, not measured from a detailed run annotation.',
    hypothesis='Weak phase/slow-bias modes may amplify linear-solver error in shooting corrections; tighter GMRES residual could improve contraction. Not established.',
    required_launch_gate='Review actual iterations and terminal/stopped status of coretripsupply01 first; do not duplicate an active6thread core job.',
    acceptance='Same residual and periodic/noise gates as source; no residual tolerance relaxation.6pointsnotRMS.',
    full_pll_acceptance=False,main_dut_modified=False)
(H/'results/core_linear_precision_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(dest.stem)
