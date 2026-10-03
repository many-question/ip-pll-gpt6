"""Repeat the same physical-core PSS with the validated three-node IC correction."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
proof=H/'results/core_seed_probe_validation.json';p=json.loads(proof.read_text())
assert p['complete'] and p['three_node_ic_correction_verified'] and p['initialization_artifact_removed']
source=H/'tb/core_pulsetrip_noise_probe_tt.scs';tb=source.read_text()
assert tb.count('core_pulsetrip_settled_tt.ic')==1
tb=tb.replace('core_pulsetrip_settled_tt.ic','core_pulsetrip_supply_seed_tt.ic')
dest=H/'tb/core_pulsetrip_supply_noise_tt.scs';assert not dest.exists();dest.write_text(tb)
out=dict(scope=__doc__,run='coretripsupply01',case=dest.stem,source_tb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
         correction_proof_sha256=hashlib.sha256(proof.read_bytes()).hexdigest(),
         change='Only readic file: add XP.vco_vdd/rx_vdd/rt_vdd=1.2V, exact zero-V probe constraints. Circuit, saves, solver and phase remain unchanged.',
         condition='Same TT27/1.2V/984MHz realLC sampled diagnostic core, static slow-control boundary.4MHz fresh PSS/1us tstab/1ps/traponly,tstart3us,10iterations.',
         first_norm_reference='Prior canceled coretripnoise01 first norm5.52e6 at XP.rt_vdd=1.2V; cancellation does not prove eventual PSS failure.',
         full_pll_acceptance=False,main_dut_modified=False,
         gates=['No initialization impulse from missing probe supplies','Actual PSS residual convergence','All branches periodic/246outputedges','Noise attribution and numerical checks'])
(H/'results/core_supply_noise_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(dest.stem)
