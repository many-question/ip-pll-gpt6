"""Read CP internal waveforms from a completed, instrumented frontend noise run.

Signed terminal currents include displacement current. Their pulse-low
averages are not automatically leakage or conduction-noise measurements.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from noise_utils import parse
from analyze_frontend_gain import measurement
from build_frontend_noise_probe import CP_OBSERVATIONS

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],required=True);a=ap.parse_args()
    pp=H/'results'/f'frontend_noise_r{a.round}_all_protocol.json'
    if not pp.exists():print('Instrumented frontend noise protocol pending');return
    p=json.loads(pp.read_text());assert p['extra_observations']==CP_OBSERVATIONS
    j=R/p['run']/p['case'];m=measurement(j,p['phase_deg'])
    if not m.get('periodic_passed'):print('Accepted frontend PSS pending');return
    raw=j/(j.name+'.raw');td=raw/'pss.td.pss';d=parse(td);assert set(CP_OBSERVATIONS)<=set(d)
    t=d['time'];T=t[-1]-t[0];mean=lambda v:float(np.trapezoid(v,t)/T)
    # Out has only VO and the two transistor drains in this specific fixture.
    kcl=d['VO:p']+d['XCP.MIP:d']+d['XCP.MPO:d']
    residual=mean(abs(kcl));scale=sum(mean(abs(d[n])) for n in ['VO:p','XCP.MIP:d','XCP.MPO:d'])
    assert scale>0
    ratio=residual/scale;checks=dict(output_terminal_kcl=ratio<1e-3)
    masks={'pulse_high':d['pulse']>.6,'pulse_low':d['pulse']<=.6,
           'gate_high':d['XCP.gate']>.6,'gate_low':d['XCP.gate']<=.6}
    nodes=['hp','hn','XCP.nb','XCP.ng','XCP.tail','XCP.mir','XCP.gate']
    currents=['VO:p','XCP.MT:d','XCP.MIP:d','XCP.MIN:d','XCP.MPO:d','XCP.MPD:d']
    windows={}
    for label,mask in masks.items():
        z=mask.astype(float);duty=mean(z);assert 0<duty<1
        windows[label]=dict(fraction=duty,mean_node_v={n:mean(d[n]*z)/duty for n in nodes},
            conditional_mean_terminal_current_a={n:mean(d[n]*z)/duty for n in currents},
            signed_terminal_charge_c={n:mean(d[n]*z)*T for n in currents})
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],source_result=m['source_result'],
             source_sha256=m['source_sha256'],td_sha256=sha(td),phase_deg=p['phase_deg'],period_s=float(T),
             output_kcl_mean_absolute_residual_a=residual,output_kcl_relative_residual=ratio,checks=checks,
             windows=windows,node_range_v={n:[float(min(d[n])),float(max(d[n]))] for n in nodes},
             full_pll_acceptance=False,limitations=['Waveforms use ideal control clamp and RF replay.',
             'No VDSsat/gm or intrinsic conduction currents are saved; these observations cannot alone establish region of operation or DC leakage.'])
    (H/'results'/f'frontend_cp_dynamics_r{a.round}.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
