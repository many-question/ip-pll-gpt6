"""Characterize the current physical reference/sampler/CP bundle before noise.

RF is the same measured, noiseless waveform replay used for the digital chain;
it is an external fixture and supplies neither LC noise nor source impedance.
Current is measured into an external DC control clamp. No PLL result is implied.
"""
from pathlib import Path
import datetime,hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    cache=ROOT/'research/runs/spectre_cmos_v14_full/coredacnoise01/core_dac_discharge_noise_tt/tstab_live_tstab_last_two_periods.npz'
    with np.load(cache) as z:t=z['time'];v=z['XP.ctrl']
    ix=t>=t[-1]-250e-9;t=t[ix];v=v[ix];clamp=float(np.trapezoid(v,t)/(t[-1]-t[0]))
    source=B/'tank_replay_full_v14.va';body=source.read_text();name='tank_replay_phase_v14'
    body=body.replace('tank_replay_full_v14',name).replace('parameter real frequency=3.936G;','parameter real frequency=3.936G;\nparameter real phase_deg=0;')
    body=body.replace('theta=2*`M_PI*frequency*$abstime;','theta=2*`M_PI*frequency*$abstime+phase_deg*`M_PI/180;')
    va=B/(name+'.va');assert not va.exists();va.write_text(body,encoding='utf-8',newline='\n')
    assert body.replace(name,'tank_replay_full_v14').replace('\nparameter real phase_deg=0;','').replace('+phase_deg*`M_PI/180','')==source.read_text()
    pdk='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
    base=f'''simulator lang=spectre
global 0
include "{pdk}" section=tt
include "{pdk}" section=stat_noise
simulator lang=spectre insensitive=no
include "cells.scs"
include "digital_cells_v2.scs"
include "sampler_bias_v5.scs"
include "cp_physical_v14.scs"
include "cp_timing.scs"
include "validity_physical_v14.scs"
ahdl_include "{name}.va"
simulatorOptions options temp=27 reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VDD (vdd 0) vsource dc=1.2
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n
XRF (vp vn 0) {name} phase_deg=PHASE
XBM (vdd 0 vmid) tx_bias_mid_v5
CCP (vp sp) capacitor c=120f
CCN (vn sn) capacitor c=120f
RBP (sp vmid) resistor r=10k
RBN (sn vmid) resistor r=10k
XREF (ref refb vdd 0) tx_reference_buffer
CR (refb 0) capacitor c=60f
// Declared control-logic loading approximation, as in the core diagnostic.
CREFLOAD (refb 0) capacitor c=1.9p
XS (refb sp sn hp hn vdd 0) tx_sampler
XCP (hp hn pulse vdd out vdd 0) cp_physical_v14 bias_r=24000
XT (refb vdd 0 pulse vdd 0) tx_cp_timing
XDET (vp hp hn amp_good phase_good vdd 0) validity_physical_v14
VO (out 0) vsource dc={clamp:.17g}
save ref refb vp vn sp sn hp hn vmid pulse out amp_good phase_good VO:p VDD:p
saveOptions options save=selected
pss pss fund=24M harms=4095 tstab=150n maxstep=1p maxacfreq=252G method=gear2only tstabmethod=gear2only errpreset=conservative maxperiods=30 saveinit=no writefinal="__FINAL_STATE__" writepss="__PERIODIC_STATE__"
'''
    rows=[]
    for phase in [0,90,180,270]:
        case=f'frontend_gain_p{phase}_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists();dest.write_text(base.replace('PHASE',str(phase)),encoding='utf-8',newline='\n')
        rows.append(dict(case=case,phase_deg=phase,run='frontendgain01',tb_sha256=sha(dest)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
        control_clamp_v=clamp,clamp_source=cache.relative_to(ROOT).as_posix(),clamp_source_sha256=sha(cache),
        clamp_window_s=[float(t[0]),float(t[-1])],rf_source_original_sha256=sha(source),rf_phase_replay_sha256=sha(va),
        rf_source_description='Same 64-cycle/20-harmonic TT waveform replay as chain_noise_rf_replay.json. New phase parameter only.',
        rf_source_protocol_sha256=sha(H/'results/chain_noise_rf_replay.json'),
        condition='TT27/1.2V/24MHzref/3.936GHzidealRF/physicalreference+sampler+CP+bias+pulser+validity; externalcontrolclamp,1.9pFrefloadapproximation.',
        current_sign='VO:p positive means the circuit delivers average current into the control clamp.',
        local_zero_selection='With positive KVCO, choose a negative d(VO:p)/d(RF phase) zero as candidate negative feedback branch. Measure local slope and centre afresh.',
        launch_scope='Four sequential gain-only cases; select and review zero before a local refinement/noise case.',
        limits=dict(endpoint_peak_v=1e-3),full_pll_acceptance=False,main_dut_modified=False,
        limitations=['Noisy LC and its impedance/backaction are absent; the clamped-current result is module evidence.',
            'Control logic is represented by1.9pF load; its active noise and exact capacitive loading are excluded.',
            'The control clamp uses a finite-window mean from a deterministic initialization trace, not an accepted PSS state.',
            'Four large phase steps locate a branch only; they do not define a local Kphi or permit jitter integration.',
            'Numerical and PVT checks remain after the operating point is selected.'])
    dest=H/'results/frontend_gain_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(control_clamp_v=clamp,cases=[x['case'] for x in rows]),indent=2))

if __name__=='__main__':main()
