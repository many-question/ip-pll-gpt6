"""Read PSF noise with units intact and check against Spectre's edge-jitter result."""
from pathlib import Path
import re,json
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent
D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_transistor_v2'
def parse(path):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(path).data.items() if k!='units'}
def header_number(path,key):
    return float(re.search('"'+re.escape(key)+'"\\s+([0-9.eE+\\-]+)',path.read_text()).group(1))
def components(path):
    lines=path.read_text().split('VALUE\n',1)[1].splitlines();result={};i=0
    while i<len(lines):
        match=re.fullmatch(r'"([^"]+)" \(',lines[i])
        if match:
            name=match[1];vals=[];i+=1
            while lines[i].strip()!=')':vals.append(float(lines[i]));i+=1
            result.setdefault(name,[]).append(vals[-1]) # 'total' is the last struct field.
        i+=1
    return {k:np.array(v) for k,v in result.items()}
def integral(f,s,lo,hi):
    assert lo>=f[0]*(1-1e-9) and hi<=f[-1]*(1+1e-9), 'No unlabelled spectrum extrapolation'
    grid=np.unique(np.r_[lo,f[(f>lo)&(f<hi)],hi])
    y=np.exp(np.interp(np.log(grid),np.log(f),np.log(np.maximum(s,1e-300))))
    return float(np.trapezoid(y,grid))
def conditions(path):
    case=path.parent.parent
    net=(case/'inputs'/(case.name+'.scs')).read_text()
    source=('PDK MOS autonomous PSS/Pnoise; ideal supply/current reference, assumed tank RLC'
            if case.name.startswith('tb_vco_') else 'PDK MOS PSS/Pnoise; ideal input clocks/supply; schematic passives')
    return dict(run=case.parent.name,corner=re.search(r'section=(tt|ss|ff)\b',net)[1],
                temperature_c=float(re.search(r'temp=([\d.]+)',net)[1]),supply_v=1.2,
                source=source)
def main():
    summary={'conditions':'See per-case corner/temperature. Ideal reference/supply, assumed passives, no spur. These are block measurements, not complete PLL jitter.', 'vco':[], 'edges':[], 'sampler_cp':[]}
    spectra={}
    for path in sorted(R.glob('*/tb_vco_*/*.raw/pn.pm.pnoise')):
        raw=path.parent;pd=parse(path);fd=parse(raw/'pss.fd.pss');td=parse(raw/'pss.td.pss')
        f=pd['relative frequency'];fosc=float(fd['freq'][1]);peak=float(abs(fd['vp'][1]-fd['vn'][1]));carrier=peak**2/2
        L=pd['out']**2/carrier
        # Spectre documents noiseout=pm as SSB, half total power; Sphi=2 L.
        totals=components(path);su=sum(totals.values())
        check=float(np.max(np.abs(su-pd['out']**2)/pd['out']**2))
        assert check<1e-6,(path,check)
        i=int(np.argmin(abs(np.log(f/1e6))))
        rank=sorted(((k,float(v[i]/su[i])) for k,v in totals.items()),key=lambda x:-x[1])
        rec=dict(run=raw.parent.parent.name,case=raw.parent.name,frequency_hz=fosc,carrier_peak_v=peak,
            phase_noise_dbc_hz={str(int(x)):float(np.interp(np.log(x),np.log(f),10*np.log10(L))) for x in [1e4,1e5,1e6,1e7]},
            free_running_jitter_10k_10m_fs=np.sqrt(2*integral(f,L,1e4,1e7))/(2*np.pi*fosc)*1e15,
            noise_sum_relative_error=check,contributors_at_1mhz=rank[:8])
        rec.update(conditions(path))
        rec['contributors_at_offsets']={str(int(off)):sorted(
            ((name,float(values[int(np.argmin(abs(np.log(f/off))))]/su[int(np.argmin(abs(np.log(f/off))))]))
             for name,values in totals.items()),key=lambda x:-x[1])[:6] for off in [1e4,1e5,1e6,1e7]}
        t=td['time'];rec['power_mw']=float(-1.2*np.trapezoid(td['VDD:p'],t)/(t[-1]-t[0])*1e3)
        summary['vco'].append(rec);key=rec['run']+'_'+rec['case'];spectra[key+'_f']=f;spectra[key+'_sphi']=2*L
    for path in sorted(R.glob('*/tb_noise_*/*.raw/pnMedge.0.sample.pnoise')):
        pd=parse(path);f=pd['freq'];slope=header_number(path,'slew rate event_1');st=pd['out']**2/slope**2
        jee=float(parse(path.parent/'pnMedge.0.Jee.pnoise')['Jee'][0])
        numeric=np.sqrt(integral(f,st,float(f[0]),float(f[-1])))
        assert abs(numeric/jee-1)<.015,(path,numeric,jee)
        rec=dict(case=path.parent.parent.name,frequency_hz=header_number(path,'fundamental frequency'),
            slew_v_per_s=slope,band_hz=[float(f[0]),float(f[-1])],spectre_jee_fs=jee*1e15,numeric_fs=numeric*1e15,
            measurement='Sampled rising-edge Jee, 0.6 V threshold; intrinsic noise with noiseless input source',
            jitter_10k_10m_fs=np.sqrt(integral(f,st,1e4,1e7))*1e15)
        rec.update(conditions(path))
        td=parse(path.parent/'pss.td.pss');t=td['time']
        rec['power_mw']=float(-1.2*np.trapezoid(td['VDD:p'],t)/(t[-1]-t[0])*1e3)
        summary['edges'].append(rec);key=rec['case'];spectra[key+'_f']=f;spectra[key+'_st']=st
    for path in sorted(list(R.glob('noise05/tb_noise_sampler*/*.raw/pn.pnoise'))+list(R.glob('noise11/tb_joint_final_center/*.raw/pn.pnoise'))+list(R.glob('noise15/tb_joint_final_center_sb1024/*.raw/pn.pnoise'))):
        pd=parse(path);f=pd['freq'];ps=components(path);su=sum(ps.values());check=float(np.max(abs(su-pd['out']**2)/pd['out']**2));assert check<1e-6
        i=int(np.argmin(abs(np.log(f/1e6))))
        td=parse(path.parent/'pss.td.pss');t=td['time'];imean=float(np.trapezoid(td['VO:p'],t)/(t[-1]-t[0]))
        rec=dict(case=path.parent.parent.name,current_asd_1mhz_a_sqrt_hz=float(pd['out'][i]),mean_clamp_current_a=imean,
            integrated_current_10k_10m_a_rms=np.sqrt(integral(f,pd['out']**2,1e4,1e7)),
            noise_sum_relative_error=check,contributors_at_1mhz=sorted(((k,float(v[i]/su[i])) for k,v in ps.items()),key=lambda x:-x[1])[:10])
        rec.update(conditions(path));rec['band_hz']=[float(f[0]),float(f[-1])]
        rec['integrated_current_full_band_a_rms']=np.sqrt(integral(f,pd['out']**2,float(f[0]),float(f[-1])))
        summary['sampler_cp'].append(rec);key=rec['case'];spectra[key+'_f']=f;spectra[key+'_si']=pd['out']**2
    if 'tb_noise_sampler_cp_sb256_si' in spectra and 'tb_noise_sampler_cp_sb512_si' in spectra:
        s0=spectra['tb_noise_sampler_cp_sb256_si'];s1=spectra['tb_noise_sampler_cp_sb512_si']
        summary['sampler_cp_psd_convergence_max_relative']=float(np.max(abs(s0/s1-1)))
    joint=[]
    for tag in ['lo','center','hi']:
        case=R/'noise11'/('tb_joint_final_'+tag)
        if not (case/'result.json').exists():break
        td=parse(case/(case.name+'.raw')/'pss.td.pss');t=td['time']
        net=(case/'inputs'/(case.name+'.scs')).read_text()
        joint.append(dict(phase_deg=float(re.search(r'sinephase=([\d.]+)',net)[1]),
                          mean_clamp_current_a=float(np.trapezoid(td['VO:p'],t)/(t[-1]-t[0]))))
    if len(joint)==3:
        kpd=(joint[2]['mean_clamp_current_a']-joint[0]['mean_clamp_current_a'])/np.deg2rad(joint[2]['phase_deg']-joint[0]['phase_deg'])
        summary['matched_detector_operating_point']=dict(points=joint,kpd_a_rad=kpd,
            residual_phase_estimate_rad=joint[1]['mean_clamp_current_a']/kpd,
            condition='3.936 GHz, 0.4 V differential peak, 0.6 V input/output common mode; 24 MHz sampling; about 2.083 ns CP pulse; PSS trap maxstep 3 ps')
    comparisons={}
    for name,a,b,kind in [('reference_31_63','tb_noise_reference','tb_noise_reference_sb63','st'),
                           ('retimer_sp25_31_63','tb_noise_retimer_sp25_tt','tb_noise_retimer_sp25_sb63','st'),
                           ('retimer_216_127_255','tb_noise_retimer_sp25_216_tt','tb_noise_retimer_sp25_216_sb255','st'),
                           ('matched_sampler_cp_512_1024','tb_joint_final_center','tb_joint_final_center_sb1024','si'),
                           ('vco_31_63','noise04_tb_vco_noise_c127_sb31','noise10_tb_vco_noise_c127_sb63','sphi')]:
        if a+'_'+kind not in spectra or b+'_'+kind not in spectra:continue
        fa=spectra[a+'_f'];fb=spectra[b+'_f']; sb=np.exp(np.interp(np.log(fa),np.log(fb),np.log(spectra[b+'_'+kind])))
        comparisons[name]=dict(max_psd_relative_difference=float(np.max(abs(spectra[a+'_'+kind]/sb-1))))
    summary['sideband_convergence']=comparisons
    (H/'results/noise_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    np.savez_compressed(H/'results/noise_spectra.npz',**spectra)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
