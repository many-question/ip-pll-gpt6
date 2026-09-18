from pathlib import Path
import sys,json,re
import numpy as np
H=Path(__file__).resolve().parent
from analyze import R
sys.path.insert(0,str(H.parent/'transistor_v2'))
from analyze_noise import parse,components

def main():
    rows=[];spectra={}
    for p in sorted(R.glob('*/*/result.json')):
        job=p.parent;raw=job/(job.name+'.raw')
        if not (raw/'pn.pm.pnoise').exists():continue
        if not json.loads(p.read_text())['ok']:continue
        assert re.search(r'spectre completes with 0 errors,',(job/'spectre.out').read_text()[-3000:])
        tb=(job/'inputs'/f'{job.name}.scs').read_text()
        harmonic=int(re.search('relharmnum=(\d+)',tb)[1])
        pd=parse(raw/'pn.pm.pnoise');fd=parse(raw/'pss.fd.pss');td=parse(raw/'pss.td.pss')
        f=pd['relative frequency'];fosc=float(fd['freq'][harmonic]);peak=float(abs(fd['vp'][harmonic]-fd['vn'][harmonic]));carrier=peak**2/2
        ssb=pd['out']**2/carrier;parts=components(raw/'pn.pm.pnoise');summed=sum(parts.values())
        err=float(np.max(abs(summed/pd['out']**2-1)));assert err<1e-6
        i=int(np.argmin(abs(np.log(f/1e6))));t=td['time']
        row=dict(run=job.parent.name,case=job.name,revision='r2' if 'fine_w=4.5e-06' in tb else 'r1',frequency_hz=fosc,carrier_peak_v=peak,harmonic=harmonic,
                 load_condition='Real divider and sampler held in tracking state (reference DC low); CP output clamped; not periodic sampling or a PLL' if harmonic==4 else '140 fF capacitive proxy on each tank node; isolated VCO',
                 offset_range_hz=[float(f[0]),float(f[-1])],maxsideband=int(re.search('maxsideband=(\d+)',tb)[1]),
                 phase_noise_dbc_hz={str(x):float(np.interp(np.log(x),np.log(f),10*np.log10(ssb))) for x in [1e4,1e5,1e6,1e7,1e8] if f[0]<=x<=f[-1]},
                 vco_power_mw=float(-1.2*np.trapezoid(td['VVCO:p'],t)/(t[-1]-t[0])*1e3),
                 total_power_mw=float(-1.2*np.trapezoid(td['VDD:p'],t)/(t[-1]-t[0])*1e3),
                 noise_psd_sum_error=err,tank_min_v=float(min(td['vp'].min(),td['vn'].min())),tank_max_v=float(max(td['vp'].max(),td['vn'].max())),
                 contributors_1mhz=sorted(((k,float(v[i]/summed[i])) for k,v in parts.items()),key=lambda x:-x[1])[:15])
        groups={}
        for k,v in parts.items():
            group='other'
            if '.XL.XP.' in k or '.XL.XN.' in k:group='inductor_RLC'
            elif '.XL.MN' in k:group='cross_coupled_core'
            elif '.XL.' in k:group='tail_and_bias'
            elif '.XBP.' in k or '.XBN.' in k:group='switched_cap_bank'
            elif k.startswith('XD.'):group='divider'
            elif k.startswith('XS.'):group='sampler'
            elif k in ['RBP','RBN'] or k.startswith('XBM.'):group='sampler_bias_network'
            elif k.startswith('XCP.'):group='charge_pump'
            groups[group]=groups.get(group,0)+float(v[i]/summed[i])
        row['fractions_1mhz']=groups;rows.append(row)
        key=job.parent.name+'__'+job.name;spectra[key+'_f']=f;spectra[key+'_L']=ssb
        print(row['case'],round(fosc/1e9,6),round(row['phase_noise_dbc_hz']['1000000.0'],3),round(row['vco_power_mw'],4),groups)
    (H/'results/noise_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    np.savez_compressed(H/'results/noise_spectra.npz',**spectra)
if __name__=='__main__':main()
