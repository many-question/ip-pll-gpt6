"""Longer diagnostic settling from the same-precision register-core endpoint.

Text terminal restart at an integer common period; not native history continuity.
An observer measures phase at internal solver steps; sparse saved RF voltages are
never used to derive GHz timing or noise. No physical DUT changes.
"""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/coreregister01/core_register_preflight_tt'
r=json.loads((j/'result.json').read_text());assert r['ok'] and r['remote_inputs_match']
assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
assert abs(r['final_values']['time']-2e-6)<1e-15
state=H/'state_inputs/core_register_2us_tt.ic';state.write_bytes((j/'final.ic').read_bytes())
s=(H/'tb/core_register_preflight_tt.scs').read_text().split('tran tran')[0]
s+='''ahdl_include "lc_loop_observer.va"
XOBS (XP.vp XP.vn XP.refb XP.ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer
tran tran stop=5u readic="core_register_2us_tt.ic" maxstep=1p strobeperiod=2n strobeoutput=strobeonly method=traponly errpreset=conservative writefinal="__FINAL_STATE__"
save obsphase obscycles obsctrl obsdivcycles XP.ctrl XP.vc1 XP.preset XP.hp XP.hn XP.en out
save XP.b0 XP.b1 XP.b2 XP.b3 XP.b4 XP.b5 XP.b6 XP.b7
saveOptions options save=selected
'''
(H/'tb/core_register_settle_tt.scs').write_text(s)
(H/'results/core_settle_protocol.json').write_text(json.dumps(dict(scope=__doc__,source_run='coreregister01',source_state_sha256=hashlib.sha256(state.read_bytes()).hexdigest(),condition='TT27/1.2V/coarse23/M4/10fF/Q5,ref-load1.9pF,1ps/reltol1e-5.5us after text2us terminal restart; not a7us continuous proof.',full_pll_acceptance=False),indent=2)+'\n')
print('Prepared5us same-core settling with solver-step phase observer.')
