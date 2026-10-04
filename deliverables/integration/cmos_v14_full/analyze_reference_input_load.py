"""Measure input edge charge from the completed reference-buffer PSS waveforms.

Q/dV is an effective switched input load under these conditions, not a linear
small-signal Cgg. Input-source impedance is zero in the underlying simulations.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/reference_buffer_noise_validation.json';v=json.loads(pp.read_text());assert v['complete'] and v['noise_all_valid']
    rows=[]
    for r in v['cases']:
        rp=ROOT/r['source_result'];assert sha(rp)==r['source_sha256']
        td=rp.parent/(rp.parent.name+'.raw')/'pss.td.pss';assert sha(td)==r['td_sha256']
        d=parse(td);t=d['time'];yr=d['ref'];current=d['VR:p']
        rise=cross(t,yr);fall=cross(t,-yr,-.6);assert len(rise)==len(fall)==1
        def charge(edge,after):
            lo=edge-50e-12;hi=edge+after;assert t[0]<=lo<hi<=t[-1]
            grid=np.r_[lo,t[(t>lo)&(t<hi)],hi]
            return float(-np.trapezoid(np.interp(grid,t,current),grid))
        sweeps=[dict(window_before_ps=50,window_after_ps=after*1e12,
                     rising_charge_c=charge(rise[0],after),falling_charge_c=charge(fall[0],after)) for after in [200e-12,500e-12,1e-9]]
        qr=sweeps[-1]['rising_charge_c'];qf=sweeps[-1]['falling_charge_c'];dv=float(max(yr)-min(yr))
        assert qr>0>qf and abs(dv/1.2-1)<1e-9
        pinrise=cross(t,yr,1.08)-cross(t,yr,.12);pinfall=cross(t,-yr,-.12)-cross(t,-yr,-1.08)
        assert len(pinrise)==len(pinfall)==1
        cap=(qr-qf)/(2*dv)
        rows.append(dict(variant=r['variant'],source_result=r['source_result'],source_sha256=r['source_sha256'],td_sha256=sha(td),
                         charge_windows=sweeps,input_swing_v=dv,measured_input_rise_10_90_ps=float(pinrise[0]*1e12),
                         measured_input_fall_90_10_ps=float(pinfall[0]*1e12),
                         effective_rising_charge_capacitance_ff=qr/dv*1e15,effective_falling_charge_capacitance_ff=-qf/dv*1e15,
                         mean_effective_charge_capacitance_ff=cap*1e15,
                         window500ps_to1ns_relative_charge_change=max(abs(qr/sweeps[1]['rising_charge_c']-1),abs(qf/sweeps[1]['falling_charge_c']-1)),
                         input_peak_current_a=r['input_peak_current_a'],
                         illustrative_rc_time_constants_ps={str(ohms):ohms*cap*1e12 for ohms in [50,500]}))
    out=dict(scope=__doc__,condition=v['condition'],source_validation_sha256=sha(pp),cases=rows,
             main_dut_modified=False,finite_source_simulated=False,full_pll_acceptance=False,
             limitations=['The source is an ideal24MHz1.2V pulse with Spectre rise/fall=10ps: measured10-90%edge is8ps.',
                          'Input current includes nonlinear gate charging and Miller coupling; Q/dV is not a bias-independent capacitance.',
                          'Illustrative50/500ohm RC constants only show scale. They are not simulated pin edges or jitter and do not establish an input specification.',
                          'Real source impedance/noise, finite rise/fall and PVT require independent circuit tests.'])
    dst=H/'results/reference_input_load_validation.json';assert not dst.exists();dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
