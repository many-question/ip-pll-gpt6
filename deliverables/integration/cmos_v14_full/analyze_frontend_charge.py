"""Measure charge partition across the CP pulse; this does not identify leakage.

Current is positive into the ideal control clamp. Displacement current and
mirror settling are included; pulse-low charge is not classified as DC leakage.
"""
from pathlib import Path
import hashlib,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_frontend_gain import measurement
from noise_utils import parse

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    names=[('frontendgain01','frontend_gain_p180_tt'),
           ('frontendroot01','frontend_root1_tt'),
           ('frontendlocal01','frontend_local1_lo_tt')]
    rows=[];fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
    for run,case in names:
        j=R/run/case;tb=(j/'inputs'/(case+'.scs')).read_text()
        phase=float(re.search(r'\bphase_deg=(\S+)',tb)[1]);m=measurement(j,phase);assert m['periodic_passed']
        raw=j/(case+'.raw');d=parse(raw/'pss.td.pss');t=d['time'];T=t[-1]-t[0]
        high=(d['pulse']>.6).astype(float);low=1-high;i=d['VO:p']
        qhigh=float(np.trapezoid(i*high,t));qlow=float(np.trapezoid(i*low,t));q=float(np.trapezoid(i,t))
        assert abs(q-qhigh-qlow)<1e-26
        duty=float(np.trapezoid(high,t)/T)
        cm=(d['hp']+d['hn'])/2;diff=d['hp']-d['hn']
        row=dict(case=case,phase_deg=phase,source_result=m['source_result'],source_sha256=m['source_sha256'],
                 td_sha256=sha(raw/'pss.td.pss'),period_s=float(T),pulse_duty=duty,
                 mean_current_a=q/T,total_charge_c=q,pulse_high_charge_c=qhigh,pulse_low_charge_c=qlow,
                 mean_current_pulse_high_a=qhigh/(duty*T),mean_current_pulse_low_a=qlow/((1-duty)*T),
                 pulse_weighted_common_mode_v=float(np.trapezoid(cm*high,t)/(duty*T)),
                 pulse_weighted_differential_v=float(np.trapezoid(diff*high,t)/(duty*T)))
        rows.append(row)
        tn=(t-t[0])*1e9;label=f'{phase:.4f} deg'
        axes[0].plot(tn,i*1e6,label=label,lw=1)
        axes[1].plot(tn,diff*1e3,label=label,lw=1)
        axes[2].plot(tn,cm,label=label,lw=1)
        if len(rows)==1:
            for ax in axes:ax.fill_between(tn,0,1,where=high>.5,transform=ax.get_xaxis_transform(),color='gray',alpha=.15)
    axes[0].set_ylabel('Clamp current (uA)');axes[1].set_ylabel('Held differential (mV)');axes[2].set_ylabel('Held common mode (V)');axes[2].set_xlabel('Time within 24 MHz period (ns)')
    for ax in axes:ax.grid(alpha=.2);ax.legend(loc='best',fontsize=8)
    fig.suptitle('Physical sampler / CP: current and held inputs\nTT 27 C, 1.2 V, noiseless 3.936 GHz RF replay; control clamp 0.66843 V')
    fig.supxlabel('Gray: pulse > 0.6 V. Pulse-low charge can include settling and displacement current; no leakage attribution.',fontsize=9)
    path=H/'figures/frontend_charge_partition.png';fig.savefig(path,dpi=140);plt.close(fig)
    out=dict(scope=__doc__,condition='TT27/1.2V, actual reference buffer, sampler, CP, pulser, bias and validity detector; noiseless RF replay 3.936GHz, 24MHz reference, clamp 0.668428925600659V.',
             cases=rows,figure=path.relative_to(ROOT).as_posix(),full_pll_acceptance=False,
             observation='At phase 180 deg, net charge is positive while charge within the nominal pulse is negative. Internal CP currents and node voltages are required before assigning a cause.',
             limitations=['Pulse threshold is 0.6 V, not a transistor conduction criterion.',
                          'Pulse-low charge is not proof of DC leakage. Mirror dynamics and displacement currents are not separated.',
                          'These are deterministic PSS waveforms, not noise or jitter measurements.'])
    (H/'results/frontend_charge_partition.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
