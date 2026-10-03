"""Prepare controlled real-LC loading tests for the two demonstrated noise candidates.

These are near-lock functional/stationarity preflights, not noise or power-up
acceptance. Baseline, RT4, CF40 and their combination share a corrected analog
seed and identical measurement topology. No candidate is adopted in main PLL.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=B/'pll_noise_pulsetrip_core_v14.scs';body=source.read_text()
seed=H/'state_inputs/core_pulsetrip_supply_seed_tt.ic'
proof=json.loads((H/'results/core_seed_probe_validation.json').read_text())
assert proof['initialization_artifact_removed'] and proof['three_node_ic_correction_verified']
base=(H/'tb/core_pulsetrip_supply_noise_tt.scs').read_text()
base=re.sub(r'^(pss |pn |edge ).*\n','',base,flags=re.M)
assert 'writefinal=' not in base and 'pss pss' not in base
base+='''
// Local time zero equals the source state at3us modulo all250ns branch periods.
// Text state is a seed, not native continuation. All three supply nodes seeded.
ahdl_include "lc_loop_observer.va"
XOBS (XP.vp XP.vn XP.refb XP.ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer
save obsphase obscycles obsctrl obsdivcycles XP.en
save XP.vco_vdd XP.rx_vdd XP.rt_vdd XP.XR.qb XP.XR.ob XP.XV.XL.nfilt
tran tran stop=3u skipdc=yes readic="core_pulsetrip_supply_seed_tt.ic" maxstep=1p strobeperiod=2n strobeoutput=strobeonly method=traponly errpreset=conservative writefinal="__FINAL_STATE__"
'''
rows=[]
for variant,rt4,cf40 in [('base',False,False),('rt4',True,False),('cf40',False,True),('rt4cf40',True,True)]:
    core='pll_noise_pulsetrip_core_v14'
    candidate=body
    if rt4:
        assert candidate.count('rt_light24s12_out083_v14')==2
        candidate=candidate.replace('rt_light24s12_out083_v14','rt_noise_scale4_v14')
    if cf40:
        assert candidate.count('lc_vco_physical_v14')==2
        candidate=candidate.replace('lc_vco_physical_v14','lc_vco_cf40_v14')
    if rt4 or cf40:
        core=f'pll_noise_{variant}_core_v14'
        candidate=candidate.replace('pll_noise_pulsetrip_core_v14',core)
        dest=B/(core+'.scs');assert not dest.exists();dest.write_text(candidate)
        # Reversal must recover the exact physical source; no hidden changes.
        reversed_body=candidate.replace(core,'pll_noise_pulsetrip_core_v14')
        if rt4:reversed_body=reversed_body.replace('rt_noise_scale4_v14','rt_light24s12_out083_v14')
        if cf40:reversed_body=reversed_body.replace('lc_vco_cf40_v14','lc_vco_physical_v14')
        assert reversed_body==body
    else:dest=source
    tb=base.replace('pll_noise_pulsetrip_core_v14',core)
    case=f'core_noisecand_{variant}_tt';p=H/'tb'/(case+'.scs');assert not p.exists();p.write_text(tb)
    rows.append(dict(case=case,variant=variant,rt_width_scale=4 if rt4 else 1,bias_cf_pf=40 if cf40 else 10,
        core=core,core_sha256=sha(dest),tb_sha256=sha(p)))
out=dict(scope=__doc__,status='prepared_not_run',run='corenoisecand01',cases=rows,
    source_core_sha256=sha(source),seed_sha256=sha(seed),
    condition='TT27/1.2V/984MHz/10fF,Q5actualLC,realRFreceiver/continuousdivider/sampledloop. Static slow-control boundary;3us/1ps/1e-5/traponly;2ns sparse observer strobes.',
    required_launch_gate='RT4 own matched precision screen must pass. Use only a released long-job slot within18threads/4long+1short; do not overlap an existing replacement pipeline.',
    acceptance='Same predeclared last1us observer criteria as coretripsettle01, coarse23 held, matching source hashes. Compare candidates against baseline under the same probes and seed.',
    limitations=['No random-jitter result: this transient has no device noise.',
                 '2ns strobes are only for observer envelopes, notGHz waveform swing, edge slope, spectrum, or power.',
                 'Reusing initial voltages across capacitance/device changes is a near-lock perturbation test, not native state continuation or cold power-up.',
                 'CF40 long bias time constant means3us stationarity alone is insufficient for final settling/noise acceptance.',
                 'Source CF10 and original RT remain in the currently running supply-corrected PSS.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_noise_candidates_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(' '.join(x['case'] for x in rows))
