"""Prepare fresh PSS only after the real-LC candidate passes transient preflight."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/coretripsettle01/core_pulsetrip_settle_tt'
validation=json.loads((H/'results/core_pulsetrip_settle_validation.json').read_text())
assert validation['preflight_passed'], 'Do not start PSS before the candidate has a stationary last1us'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(j/'result.json')==validation['source_sha256']
r=json.loads((j/'result.json').read_text());source=j/'final.ic'
assert r['remote_inputs_match'] and sha(source)==r['local_outputs_sha256']['final.ic']
state=H/'state_inputs/core_pulsetrip_settled_tt.ic';assert not state.exists()
lines=[line for line in source.read_text().splitlines() if line.strip() and
       (line.split()[0].startswith('XP.') or line.split()[0] in ['out','ref','vdd'])]
assert any(line.startswith('XP.XV.') for line in lines) and any(line.startswith('XP.XD.') for line in lines)
state.write_text('# Candidate3us final state, observer-only states excluded; text seed, not native checkpoint.\n'+'\n'.join(lines)+'\n')
tb=(H/'tb/core_register_noise_restart_tt.scs').read_text()
tb=tb.replace('pll_noise_register_core_v14','pll_noise_pulsetrip_core_v14')
tb=tb.replace('tstart=5u tstab=250n','tstart=3u tstab=1u')
tb=tb.replace('core_register_settled_tt.ic',state.name)
tb=tb.replace('method=gear2only tstabmethod=gear2only','method=traponly tstabmethod=traponly')
tb=tb.replace('maxperiods=8','maxperiods=10')
tb+='\nsave XP.XD.ct0 XP.XD.ct1 XP.XD.cb XP.XD.d6 XP.XD.r0 XP.XD.r4 XP.XD.r6 XP.XD.fb\n'
target=H/'tb/core_pulsetrip_noise_probe_tt.scs';assert not target.exists();target.write_text(tb)
out=dict(scope=__doc__,planned_run='coretripnoise01',case=target.stem,
    source_validation_sha256=sha(H/'results/core_pulsetrip_settle_validation.json'),source_state_sha256=sha(source),seed_sha256=sha(state),
    condition='TT27/1.2V/984MHz/10fF, real LC Q5 and sampled loop, physical continuous-clock divider; fixed slow-control boundary, CF10pF and baseline retimer.',
    solver='Fresh4MHz PSS,1us stabilization,1ps/1e-5,traponly matches source transient; tstart3us matches source phase.4095harms/sidebands,10iterations maximum.',
    hypothesis='Changes both physical dynamic-node clocking and uses matched-source integration. Not a one-variable solver benchmark.',
    full_pll_acceptance=False,main_dut_modified=False,
    gates=['Source preflight passed','PSS actual convergence, no failed-state reuse','All active branches periodic in250ns,246output rising edges','Device PSD sums and noise-on before any jitter claim'])
(H/'results/core_pulsetrip_noise_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(target.stem)
