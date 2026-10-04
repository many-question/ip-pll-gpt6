"""Analyze accepted frontend PSS dynamics before final PNoise completion."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,cross
from build_frontend_noise_probe import CP_OBSERVATIONS
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    raw=ROOT/'research/diagnostics/frontend_noise2all_pss_snapshot01';mp=raw/'manifest.json'
    m=json.loads(mp.read_text());pp=H/'results/frontend_noise_r2_all_protocol.json';p=json.loads(pp.read_text())
    assert m['protocol_sha256']==sha(pp) and m['hashes_stable_during_transfer'] and m['accepted_pss_observed']
    assert all(sha(raw/k)==v['sha256'] for k,v in m['files'].items())
    assert sha(raw/'spectre_at_snapshot.out')==m['log_sha256']
    d=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');assert set(CP_OBSERVATIONS)<=set(d)
    t=d['time'];T=t[-1]-t[0];mean=lambda v:float(np.trapezoid(v,t)/T)
    nodes=['ref','refb','vp','vn','sp','sn','hp','hn','vmid','pulse','out','amp_good','phase_good']
    endpoint=max(float(abs(d[n][-1]-d[n][0])) for n in nodes)
    counts=dict(rf=len(cross(t,d['vp']-d['vn'],0)),ref=len(cross(t,d['refb'])),pulse=len(cross(t,d['pulse'])))
    harmonic=int(1+np.argmax(abs((fd['vp']-fd['vn'])[1:])))
    balanced=abs(mean(d['VO:p']))/p['kphi_magnitude_a_per_rf_rad']<p['balanced_phase_limit_rad']
    periodic=bool(abs(T*24e6-1)<1e-7 and endpoint<1e-3 and counts==dict(rf=164,ref=1,pulse=1) and harmonic==164)
    valid=bool(mean((d['amp_good']>.6).astype(float))>.999 and mean((d['phase_good']>.6).astype(float))>.999)
    assert periodic and balanced and valid
    kcl=d['VO:p']+d['XCP.MIP:d']+d['XCP.MPO:d']
    residual=mean(abs(kcl));scale=sum(mean(abs(d[n])) for n in ['VO:p','XCP.MIP:d','XCP.MPO:d']);assert scale>0
    windows={};nodes=['hp','hn','XCP.nb','XCP.ng','XCP.tail','XCP.mir','XCP.gate']
    currents=['VO:p','XCP.MT:d','XCP.MIP:d','XCP.MIN:d','XCP.MPO:d','XCP.MPD:d']
    for label,mask in dict(pulse_high=d['pulse']>.6,pulse_low=d['pulse']<=.6,gate_high=d['XCP.gate']>.6,gate_low=d['XCP.gate']<=.6).items():
        z=mask.astype(float);duty=mean(z);assert 0<duty<1
        windows[label]=dict(fraction=duty,mean_node_v={n:mean(d[n]*z)/duty for n in nodes},
                           conditional_mean_terminal_current_a={n:mean(d[n]*z)/duty for n in currents},
                           signed_terminal_charge_c={n:mean(d[n]*z)*T for n in currents})
    out=dict(scope=__doc__,condition=p['condition'],source_snapshot=mp.relative_to(ROOT).as_posix(),
             source_snapshot_sha256=sha(mp),protocol_sha256=sha(pp),phase_deg=p['phase_deg'],period_s=float(T),
             waveform_checks=dict(periodic=periodic,balanced=bool(balanced),validity=valid,output_kcl=residual/scale<1e-3),
             endpoint_peak_v=endpoint,edge_counts=counts,rf_dominant_harmonic=harmonic,
             mean_clamp_current_a=mean(d['VO:p']),output_kcl_mean_absolute_residual_a=residual,
             output_kcl_relative_residual=residual/scale,windows=windows,
             node_range_v={n:[float(min(d[n])),float(max(d[n]))] for n in nodes},
             final_job_complete=False,noise_measured=False,full_pll_acceptance=False,
             limitations=['Snapshot of accepted PSS, not final simulation completion or PNoise output.',
                          'Terminal currents include displacement; pulse-low current is not automatically DC leakage.',
                          'No intrinsic conduction current, gm or VDSsat measurements; no region-of-operation conclusion.',
                          'Ideal RF replay and control clamp omit actual LC interaction.'])
    (H/'results/frontend_pss_snapshot_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
