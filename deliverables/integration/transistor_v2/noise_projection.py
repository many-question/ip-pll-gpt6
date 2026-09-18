"""Diagnostic continuous-loop projection of measured device noise, NOT PLL signoff.

The circuit spectra come from different isolated benches. No correlation,
sampled-loop aliases, reference images, VCO clock driver or supply noise included.
The low-band reference term is deliberately labelled partial. No spectrum is
extrapolated beyond its measured band. This calculation locates design risks.
"""
from pathlib import Path
import json,sys
import numpy as np
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'architecture/behavioral_v1'))
from model import Loop,impedance,continuous_open,sampled_matrices

def main():
    z=np.load(H/'results/noise_spectra.npz')
    summary=json.loads((H/'results/noise_summary.json').read_text())
    kpd=summary['matched_detector_operating_point']['kpd_a_rad']
    f=np.geomspace(1e4,492e6,20000)
    def spectrum(key,kind,grid=f):
        ff=z[key+'_f'];ss=z[key+'_'+kind]
        assert grid[0]>=ff[0]*(1-1e-10) and grid[-1]<=ff[-1]*(1+1e-10)
        return np.exp(np.interp(np.log(grid),np.log(ff),np.log(ss)))
    def rms(s,grid=f):return float(np.sqrt(np.trapezoid(s,grid))*1e15)
    rows=[]
    # 30 MHz/V is a labelled high-band sensitivity hypothesis, not this PSS's Kvco.
    # R -> a*R, C -> C/a**2 scales the continuous loop frequency by a.
    for speed in [1,2,4]:
        lp=Loop(24e6,kpd,2*np.pi*30e6,100e3*speed,28.6479e-12/speed**2,1.90986e-12/speed**2,.05,.05)
        g=continuous_open(lp,f);s=1/(1+g);h=g*s
        unity=float(np.exp(np.interp(0,np.log(abs(g))[::-1],np.log(f)[::-1])))
        phase_margin=float(180+np.interp(np.log(unity),np.log(f),np.unwrap(np.angle(g)))*180/np.pi)
        rho=float(max(abs(np.linalg.eigvals(sampled_matrices(lp)[0]))))
        phase_to_time=(2*np.pi*3.936e9)**2
        cp=rms(abs(h)**2*spectrum('tb_joint_final_center','si')/kpd**2/phase_to_time)
        rnoise=4*1.380649e-23*300.15*np.real(impedance(lp,f))
        resistor=rms(abs(s)**2*(lp.kv/(2*np.pi*f))**2*rnoise/phase_to_time)
        fo=z['tb_noise_reference_slow_improved_f'];ref=rms(abs(continuous_open(lp,fo)/(1+continuous_open(lp,fo)))**2*spectrum('tb_noise_reference_slow_improved','st',fo),fo)
        output=rms(spectrum('tb_noise_retimer_sp25_tt','st'))
        for key in ['noise04_tb_vco_noise_c0','noise06_tb_vco_filtered_c0','noise14_tb_vco_filtered_slow_c0']:
            if key+'_f' not in z:continue
            vrec=next(x for x in summary['vco'] if x['run']+'_'+x['case']==key)
            vco=rms(abs(s)**2*spectrum(key,'sphi')/(2*np.pi*vrec['frequency_hz'])**2)
            components=dict(vco=vco,sampler_and_cp=cp,filter_resistor=resistor,
                            reference_buffer_10k_12m_only=ref,retimer_and_output=output)
            rows.append(dict(vco_source=key,loop_frequency_scale=speed,rlf_ohm=lp.r,c1_f=lp.c1,c2_f=lp.c2,kvco_assumed_hz_v=30e6,kpd_measured_a_rad=kpd,
                unity_hz=unity,continuous_phase_margin_deg=phase_margin,sampled_linear_spectral_radius=rho,
                component_fs=components,partial_rss_fs=float(np.sqrt(sum(x*x for x in components.values())))))
    result=dict(status='diagnostic estimate; not measured PLL jitter and not a pass/fail test',
        band_hz=[1e4,492e6],output_assumed_hz=984e6,rows=rows,
        limitations=['Isolated unloaded VCO near 4.036 GHz used as high-band source; loaded operating point differs.',
          'Kvco 30 MHz/V is a sensitivity assumption; sampled detector gain extracted at ideal 0.4 V differential RF peak.',
          'Continuous transfer: sampled alias coupling and reference spectral images omitted.',
          'Only reference-buffer noise from 10 kHz to 12 MHz; external reference, real VCO clock driver and supply coupling omitted.',
          'Ideal passives; no extracted parasitics, mismatch or statistical yield. RC alternatives are unvalidated circuit proposals.'])
    (H/'results/noise_projection.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
