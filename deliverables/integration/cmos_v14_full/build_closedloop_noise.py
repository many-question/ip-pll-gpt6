"""Closed-loop device-noise fixture derived from pll_capture_v14.

Retains the actual analog feedback loop, physical bias, full divider bank,
retimer, detector, CP timing, disconnected physical DAC and quiet counter load.
FLL/configuration/supervision are replaced by fixed acquired-state control pins.
This is a locked-core approximation, NOT full-PLL noise acceptance.
"""
from pathlib import Path
import hashlib,json,re,datetime
H=Path(__file__).resolve().parent; ROOT=H.parents[3]; B=H.parents[1]/'blocks/cmos_v14_full'
source=B/'pll_capture_v14.scs'; s=source.read_text()
s=s.replace('pll_capture_v14','pll_noise_core_v14')
s=re.sub(r'^subckt pll_noise_core_v14 .*$', 'subckt pll_noise_core_v14 (ref out vdd vss)',s,flags=re.M)
s=re.sub(r'^XC .*\n','',s,flags=re.M)
# Fixed codes are external DC sources at the diagnostic boundary, not a new PLL.
extra=['// Diagnostic acquired state: coarse23, DAC38, M4; ideal static controls.']
for node,value in [('en',1.2),('divider_reset',0),('acquired',1.2),('acquired_b',0)]+[(f'b{i}',1.2*((23>>i)&1)) for i in range(8)]+[(f'd{i}',1.2*((38>>i)&1)) for i in range(6)]+[(f's{i}',1.2*(i==0)) for i in range(6)]:
 extra.append(f'VFIX_{node} ({node} vss) vsource dc={value:g}')
extra+=['XCPULSE (refb en vss pulse vdd vss) tx_cp_timing',
 'XDAC (d0 d1 d2 d3 d4 d5 acquired preset vdd vss) tx_fll_dac',
 'XACQ0 (acqclk clock_mux acquired_b acquired vdd vss) pll_tg wn=1u wp=2u',
 'XACQ1 (out clock_mux acquired acquired_b vdd vss) pll_tg wn=1u wp=2u',
 'XACB0 (clock_mux clock_b vdd vss) pll_inv wn=1u wp=2u',
 'XACB1 (clock_b count_clock vdd vss) pll_inv wn=2u wp=4u',
 'XCOUNT (count_clock vss vdd q0 qx1 q2 q3 q4 q5 q6 q7 q8 q9 q10 q11 q12 q13 vdd vss) tx_fll_counter']
s=s.replace('ends pll_noise_core_v14','\n'.join(extra)+'\nends pll_noise_core_v14')
(B/'pll_noise_core_v14.scs').write_text(s)
original=ROOT/'research/runs/spectre_cmos_v14_full/repaircold01/repair_capture_tt/final.ic'
lines=['# Starting guess only; extracted from actual TT coarse23/DAC38 capture at64us.']
maps={'XP.XC.XP.':'XP.XCPULSE.','XP.XC.XDAC.':'XP.XDAC.','XP.XC.XACQ':'XP.XACQ','XP.XC.XACB':'XP.XACB','XP.XC.XCOUNT.':'XP.XCOUNT.'}
for line in original.read_text().splitlines():
 if line.startswith('#') or not line.strip():continue
 node=line.split()[0]
 if node.startswith('XP.') and not node.startswith('XP.XC.') or node=='out':lines.append(line)
 else:
  for old,new in maps.items():
   if node.startswith(old):lines.append(line.replace(old,new,1));break
(H/'state_inputs/closedloop_core_tt.ic').write_text('\n'.join(lines)+'\n')
base=(H/'tb/repair_retain_tt.scs').read_text().split('include "pll_capture_v14.scs"')[0]
base+='''include "pll_noise_core_v14.scs"
simulatorOptions options temp=27 reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VDD (vdd 0) vsource dc=1.2
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n
XP (ref out vdd 0) pll_noise_core_v14
CL (out 0) capacitor c=10f
'''
save='''save ref out XP.vp XP.vn XP.ctrl XP.vc1 XP.refb XP.hp XP.hn XP.pulse XP.clk XP.q1 XP.data XP.acqclk XP.XD.d8 XP.XD.d12 XP.preset VDD:p XP.VVCO:p XP.VRX:p XP.VRT:p
saveOptions options save=selected
'''
# Keep full transient points for the preflight; no phase observer enters PSS.
(H/'tb/core_preflight_tt.scs').write_text(base+'''tran tran stop=1u readic="closedloop_core_tt.ic" maxstep=1p method=traponly errpreset=conservative writefinal="__FINAL_STATE__"
'''+save)
for label,sweep in [('probe','values=[10k 100k 1M 10M 100M 491.99M]'),('band','start=10k stop=492M dec=20')]:
 tb=base+f'''// lcm(24MHz reference, RF/8,RF/12) =>250ns;246 output edges.
pss pss fund=4M harms=4095 tstab=1u readic="closedloop_core_tt.ic" maxstep=1p method=traponly errpreset=conservative maxperiods=12 saveinit=yes writefinal="__FINAL_STATE__" writepss="__PERIODIC_STATE__"
pn pnoise {sweep} pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=246 maxsideband=4095
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
'''+save
 (H/'tb'/f'core_noise_{label}_tt.scs').write_text(tb)
protocol=dict(created=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,
 source_top=source.relative_to(ROOT).as_posix(),source_top_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 state_source=original.relative_to(ROOT).as_posix(),state_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
 condition='TT27/1.2V/ideal24MHz reference/K41/M4/984MHz/10fF/Q5RLC/coarse23/DAC38',
 included=['VCO and physical bias','reference buffer and sampler','CP and physical pulse timing','loop RC and precharge switches','full programmable divider bank','RF receiver and retimer/output','physical validity detector','disabled physical DAC','quiet physical counter clock load'],
 excluded=['FLL/configuration/supervisor/watchdog noise and changing state','their reference-input loading','dynamic counter activity','finite output impedance/noise of static control bits','external reference and supply noise','PEX'],
 gates=['converged periodic solution and correct 4MHz fundamental,984MHz output','compare analog operating point and reference edge against full-DUT transient','full10kHz-492MHz PSD/slew^2 integration','edge-position and finite-neighborhood alias checks','numerical step/sideband convergence','separate per-module noise-on validation'],
 full_pll_acceptance=False,probe_is_not_integral=True)
(H/'results/closedloop_noise_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
print('Prepared locked-core transient and PSS/PNoise fixtures; full PLL remains unverified.')
