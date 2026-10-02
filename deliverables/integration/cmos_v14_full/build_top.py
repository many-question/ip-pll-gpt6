"""First complete physical acquisition/mainloop path atK41/M4; six-mode bank follows."""
from pathlib import Path
H=Path(__file__).resolve().parent;D=H.parents[1];B=D/'blocks/cmos_v14_full'
incs=['cells.scs','digital_cells_v2.scs','fll_circuit.scs','fll_controller_full_v14.scs','pll_config.scs','pll_supervisor.scs','frequency_watchdog.scs','cp_timing.scs','pll_control_full_v14.scs','lc_vco_physical_v14.scs','cp_physical_v14.scs','sampler_bias_v5.scs','loop_filter_v5.scs','rf_light24s12_v14.scs','div_fb50buf24_v14.scs','rtcomb_v13.scs','rt_light24s12_out083_v14.scs','validity_physical_v14.scs']
s=['simulator lang=spectre']+[f'include "{f}"' for f in incs]
s += ['// First integration is explicitly K41/M4. Other K codes are not supported by this proof top.',
 'subckt pll_complete_k41_v14 (ref reset apply k0 k1 k2 k3 k4 k5 out qualified range_error cfg_ready frequency_good phase_good amp_good vdd vss)',
 'parameters bias_r=2500 cp_bias_r=24000 rlf=100k',
 'VVCO (vco_vdd vdd) vsource dc=0','VRX (rx_vdd vdd) vsource dc=0','VRT (rt_vdd vdd) vsource dc=0',
 'XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vco_vdd vss) lc_vco_physical_v14 bias_r=bias_r',
 'XBM (vdd vss vmid) tx_bias_mid_v5','CCP (vp sp) capacitor c=120f','CCN (vn sn) capacitor c=120f','RBP (sp vmid) resistor r=10k','RBN (sn vmid) resistor r=10k',
 'XREF (ref refb vdd vss) tx_reference_buffer','CR (refb vss) capacitor c=60f','XS (refb sp sn hp hn vdd vss) tx_sampler',
 'XCP (hp hn pulse en ctrl vdd vss) cp_physical_v14 bias_r=cp_bias_r',
 'XLF (ctrl vc1 en preset vdd vss) tx_loop_filter_v5 rlf=rlf',
 'XRX (vp clk rx_vdd vss) rf_light24s12_v14','XD (clk q1 data vdd vss) div_fb50buf24_v14','XR (data clk out rt_vdd vss) rt_light24s12_out083_v14',
 'XDET (vp hp hn amp_good phase_good vdd vss) validity_physical_v14',
 'XC (refb reset apply k0 k1 k2 k3 k4 k5 out phase_good frequency_good b0 b1 b2 b3 b4 b5 b6 b7 s0 s1 s2 s3 s4 s5 divider_reset en pulse preset qualified range_error cfg_ready cfg_invalid restart count_gate count_reset vdd vss) pll_control_full_v14',
 'ends pll_complete_k41_v14']
(B/'pll_complete_k41_v14.scs').write_text('\n'.join(s)+'\n')
model='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
for c,temp in [('tt',27),('ss',60),('ff',0)]:
 s=[f'simulator lang=spectre\nglobal 0\ninclude "{model}" section={c}',f'include "{model}" section=stat_noise','simulator lang=spectre insensitive=no',f'include "{model}" section={c}_bbmvar','simulator lang=spectre insensitive=no','include "pll_complete_k41_v14.scs"',
 f'simulatorOptions options temp={temp} reltol=1e-4 vabstol=1e-6 iabstol=1e-12',
 'VDD (vdd 0) vsource dc=1.2',
 'VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n',
 'VRST (reset 0) vsource type=pwl wave=[0 1.2 200n 1.2 200.01n 0]',
 'VAP (apply 0) vsource type=pwl wave=[0 0 300n 0 300.01n 1.2 500n 1.2 500.01n 0]']
 for i in range(6):s.append(f'VK{i} (k{i} 0) vsource dc={1.2 if (41>>i)&1 else 0}')
 s+=['XP (ref reset apply k0 k1 k2 k3 k4 k5 out qualified range_error cfg_ready frequency_good phase_good amp_good vdd 0) pll_complete_k41_v14',
     'CL (out 0) capacitor c=10f','ahdl_include "lc_loop_observer.va"',
     'XOBS (XP.vp XP.vn XP.refb XP.ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer',
     'ic XP.vp=1.20001 XP.vn=1.2',
     'tran tran stop=42u maxstep=4p strobeperiod=2n strobeoutput=strobeonly method=traponly errpreset=moderate writefinal="__FINAL_STATE__"',
     'save obsphase obscycles obsctrl obsdivcycles out ref qualified range_error cfg_ready frequency_good phase_good amp_good XP.ctrl XP.vc1 XP.preset XP.en XP.hp XP.hn XP.XV.XL.nb XP.XV.XL.nfilt XP.XV.XL.tail VDD:p XP.VVCO:p XP.VRX:p XP.VRT:p',
     'save XP.count_gate XP.count_reset XP.restart XP.XC.acquired XP.XC.state0 XP.XC.state1 XP.XC.state2 '+' '.join('XP.b'+str(i) for i in range(8))+' '+' '.join('XP.XC.d'+str(i) for i in range(6))+' '+' '.join('XP.XC.m'+str(i) for i in range(14)),
     'saveOptions options save=selected']
 (H/'tb'/f'acquire_k41_{c}.scs').write_text('\n'.join(s)+'\n')
print('Built complete physical K41 path and three acquisition TBs')
