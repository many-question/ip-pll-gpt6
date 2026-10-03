"""Restore physical coarse-code drivers in the diagnostic closed-loop core.

An ideal voltage at each cap-bank gate removes driver impedance and RF feedthrough.
Use the same resettable MOS DFFs as the actual FLL's eight code registers, held
through D=q feedback. This is still a diagnostic reduction, not full PLL noise.
"""
from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
s=(B/'pll_noise_loadprobe_v14.scs').read_text().replace('pll_noise_loadprobe_v14','pll_noise_register_core_v14')
for bit in range(8):
 s=re.sub(r'^VFIX_b'+str(bit)+r' .*$',f'XCOARSE{bit} (b{bit} refb vss b{bit} vdd vss) tx_dff_r0',s,flags=re.M)
(B/'pll_noise_register_core_v14.scs').write_text(s)
source=ROOT/'research/runs/spectre_cmos_v14_full/repaircold01/repair_capture_tt/final.ic'
ic=(H/'state_inputs/closedloop_core_tt.ic').read_text().splitlines()
for line in source.read_text().splitlines():
 for bit in range(8):
  old=f'XP.XC.XF.X{bit+3}.'
  if line.startswith(old):ic.append(line.replace(old,f'XP.XCOARSE{bit}.',1));break
(H/'state_inputs/core_register_tt.ic').write_text('\n'.join(ic)+'\n')
tb=(H/'tb/core_load2p_tt.scs').read_text().replace('pll_noise_loadprobe_v14','pll_noise_register_core_v14').replace('closedloop_core_tt.ic','core_register_tt.ic').replace('ref_load=2p','ref_load=1.9p').replace('stop=300n','stop=2u')
tb+='save '+' '.join(f'XP.b{i}' for i in range(8))+'\n'
(H/'tb/core_register_preflight_tt.scs').write_text(tb)
scope='TT27/1.2V/1ps/reltol1e-5,2us; same physical FLL coarse-output DFF cells clocked by actual refb,D=q,initialized from actual64us terminal. Additional1.9pF reference load is diagnostic approximation, not extracted logic. Other ideal static controls and omitted slow logic remain. No PNoise accepted until stationary operating point checked.'
(H/'results/core_register_protocol.json').write_text(json.dumps(dict(scope=scope,source_ic=source.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),physical_code_registers=8,full_pll_acceptance=False),indent=2)+'\n')
print(scope)
