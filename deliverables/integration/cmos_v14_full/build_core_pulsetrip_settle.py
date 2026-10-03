"""Physical-core candidate to test continuous divider clocks before fresh PSS.

Only the divider bank changes. The settled analog state is a text seed, not
native continuation. No functional or noise acceptance is implied by building.
"""
from pathlib import Path
import hashlib
import json

H = Path(__file__).resolve().parent
B = H.parents[1] / 'blocks/cmos_v14_full'
source = B / 'pll_noise_register_core_v14.scs'
body = source.read_text()
assert body.count('cmos_even_bank_acq_v14') == 2
body = body.replace('cmos_even_bank_acq_v14', 'bank_pulsetrip_v14')
body = body.replace('pll_noise_register_core_v14', 'pll_noise_pulsetrip_core_v14')
target = B / 'pll_noise_pulsetrip_core_v14.scs'
assert not target.exists()
target.write_text(body, encoding='utf-8', newline='\n')
state = H / 'state_inputs/core_register_settled_tt.ic'
target_state = H / 'state_inputs/core_pulsetrip_analog_seed_tt.ic'
assert not target_state.exists()
removed, kept = [], []
changed_nodes = {'out', 'XP.q1', 'XP.data', 'XP.acqclk', 'XP.clock_mux',
                 'XP.clock_b', 'XP.count_clock'}
for line in state.read_text().splitlines():
    if not line.strip() or line.startswith('#'):
        continue
    name = line.split()[0]
    if name.startswith(('XP.XD.', 'XP.XR.', 'XP.XACQ', 'XP.XACB', 'XP.XCOUNT.')) or name in changed_nodes:
        removed.append(name)
    else:
        kept.append(line)
assert any(x.startswith('XP.XD.') for x in removed)
target_state.write_text('# Analog and coarse-register seed from coressettle01; changed divider/output states omitted.\n' + '\n'.join(kept) + '\n')
tb = (H / 'tb/core_register_settle_tt.scs').read_text()
tb = tb.replace('pll_noise_register_core_v14', 'pll_noise_pulsetrip_core_v14')
tb = tb.replace('stop=5u', 'stop=3u skipdc=yes')
tb = tb.replace('core_register_2us_tt.ic', target_state.name)
tb += '\nsave XP.XD.ck XP.XD.load XP.XD.loadb XP.q1 XP.data XP.acqclk\n'
target_tb = H / 'tb/core_pulsetrip_settle_tt.scs'
assert not target_tb.exists()
target_tb.write_text(tb, encoding='utf-8', newline='\n')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = dict(scope=__doc__, planned_run='coretripsettle01', case=target_tb.stem,
           source_core_sha256=sha(source), candidate_core_sha256=sha(target),
           source_state_sha256=sha(state), candidate_state_sha256=sha(target_state),
           removed_state_nodes=removed, kept_state_count=len(kept),
           change='Original clock-gated divider replaced by bank_pulsetrip_v14; baseline RT, VCO CF10pF, CP and loop filter unchanged.',
           hypothesis='Continuously clocked reset/ring nodes may avoid the floating dynamic states implicated in failed core shooting; not yet a proven root cause.',
           condition='TT27/1.2V/984MHz/10fF, actual LC Q5, actual sampled loop/coarse registers, static acquired control boundary; 3us/1ps/1e-5.',
           phase_alignment='Source ends at5us, an integer multiple of the250ns full-circuit period; reset local time0 and settle again.',
           acceptance='Same last1us stationarity criteria as analyze_core_settle.py; then fresh PSS with periodic-node audit before noise.',
           main_dut_modified=False, full_pll_acceptance=False)
(H / 'results/core_pulsetrip_protocol.json').write_text(json.dumps(out, indent=2)+'\n')
print(target_tb.stem, 'state nodes kept', len(kept), 'removed', len(removed))
