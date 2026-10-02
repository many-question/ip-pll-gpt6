"""Characterize current physical output chain with replayed RF, not full-PLL noise.

The RF replay is an external, noiseless zero-impedance testbench stimulus.
Actual receiver/divider/retimer are retained. A physical shared-counter clock load
is included in its reset, quiet state. VCO/main-loop/reference noise is excluded.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
p=ROOT/'research/runs/spectre_cmos_v14_full/completedense01/complete_warm_tt/waveforms.npz'
with np.load(p) as z:d={k:z[k] for k in ['time','XP.vp','XP.vn']}
t=d['time'];e=cross(t,d['XP.vp']-d['XP.vn'],0);e=e[-65:]
phase=np.arange(1024)/1024;theta=2*np.pi*phase
matrix=np.column_stack([np.ones(len(phase))]+[f(n*theta) for n in range(1,21) for f in [np.cos,np.sin]])
body=['`include "disciplines.vams"','`include "constants.vams"','// External measured-waveform replay only; not an internal VCO model.',
 'module tank_replay_full_v14(vp,vn,vss);','output vp,vn;input vss;electrical vp,vn,vss;','parameter real frequency=3.936G;','real theta;','analog begin','theta=2*`M_PI*frequency*$abstime;']
meta=dict(scope=__doc__,source=str(p.relative_to(ROOT)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),rf_hz=3936e6,cycles_averaged=len(e)-1,source_window_us=[float(e[0]*1e6),float(e[-1]*1e6)],fit={})
for port in ['vp','vn']:
    wave=np.array([np.interp(a+(b-a)*phase,t,d['XP.'+port]) for a,b in zip(e[:-1],e[1:])]);avg=wave.mean(axis=0)
    coef=np.linalg.lstsq(matrix,avg,rcond=None)[0];fit=matrix@coef
    expr=f'{coef[0]:.16g}'+''.join(f'+({coef[2*n-1]:.16g})*cos({n}*theta)+({coef[2*n]:.16g})*sin({n}*theta)' for n in range(1,21))
    body.append(f'V({port},vss)<+{expr};')
    meta['fit'][port]=dict(dc_v=float(coef[0]),range_v=[float(min(avg)),float(max(avg))],rms_fit_error_v=float(np.sqrt(np.mean((fit-avg)**2))),max_fit_error_v=float(max(abs(fit-avg))),max_cycle_deviation_v=float(max(abs(wave-avg).flatten())),coefficients=coef.tolist())
body+=['end','endmodule'];(B/'tank_replay_full_v14.va').write_text('\n'.join(body)+'\n')
(H/'results/chain_noise_rf_replay.json').write_text(json.dumps(meta,indent=2)+'\n')
base='''simulator lang=spectre
global 0
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section=tt
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section=stat_noise
simulator lang=spectre insensitive=no
include "cells.scs"
include "digital_cells_v2.scs"
include "fll_circuit.scs"
include "rf_light24s12_v14.scs"
include "cmos_even_bank_acq_v14.scs"
include "rtcomb_v13.scs"
include "rt_light24s12_out083_v14.scs"
simulatorOptions options reltol=1e-5 vabstol=1e-7 iabstol=1e-13 temp=27
VDD (vdd 0) vsource dc=1.2
ahdl_include "tank_replay_full_v14.va"
XRF (vp vn 0) tank_replay_full_v14
VRX (rx_vdd vdd) vsource dc=0
VRT (rt_vdd vdd) vsource dc=0
XRX (vp clk rx_vdd 0) rf_light24s12_v14
VRST (reset 0) vsource type=pwl wave=[0 1.2 20n 1.2 20.01n 0]
XD (clk reset vdd 0 0 0 0 0 q1 data acqclk vdd 0) cmos_even_bank_acq_v14
XR (data clk out rt_vdd 0) rt_light24s12_out083_v14
CL (out 0) capacitor c=10f
// Same clock mux/buffers/counter input load, counter held reset in quiet phase.
XACQ0 (acqclk clock_mux 0 vdd vdd 0) pll_tg wn=1u wp=2u
XACQ1 (out clock_mux vdd 0 vdd 0) pll_tg wn=1u wp=2u
XACB0 (clock_mux clock_b vdd 0) pll_inv wn=1u wp=2u
XACB1 (clock_b count_clock vdd 0) pll_inv wn=2u wp=4u
XCOUNT (count_clock 0 vdd q0 qx1 q2 q3 q4 q5 q6 q7 q8 q9 q10 q11 q12 q13 vdd 0) tx_fll_counter
'''
for label,step,side in [('coarse','1p',383),('fine','0.5p',767)]:
    s=base+f'''// Full divider-tree period is24 RF cycles; output has6 rising edges.
pss pss fund=164M harms={side} tstab=300n maxstep={step} method=traponly errpreset=conservative maxperiods=30 saveinit=no writefinal="__FINAL_STATE__"
pn pnoise start=10k stop=492M dec=10 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=6 maxsideband={side}
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
save vp vn clk q1 data out acqclk XD.d8 XD.d12 VDD:p VRX:p VRT:p
saveOptions options save=selected
'''
    (H/'tb'/('chain_noise_'+label+'_tt.scs')).write_text(s)
print(json.dumps({k:v for k,v in meta.items() if k!='fit'},indent=2));print({k:{x:y for x,y in v.items() if x!='coefficients'} for k,v in meta['fit'].items()})
