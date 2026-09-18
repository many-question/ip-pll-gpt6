from pathlib import Path
import sys,json,re
import numpy as np
H=Path(__file__).resolve().parent;D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_transistor_v3'
sys.path.insert(0,str(H.parent/'transistor_v2'))
from analyze_noise import parse,components,integral

def main():
 result={'vco':[],'sampler_cp':[],'diagnostic_note':'noise01 contains an off-zero R1 center and a later R2 high endpoint. Do not use its inferred gain for signoff; safe_sampler_cp uses matched R2 inputs.'};spectra={}
 points=[]
 for tag in ['lo','hi']:
  case=f'tb_joint_safe_{tag}';p=R/'safe_gain01'/case
  td=parse(p/f'{case}.raw'/'pss.td.pss');t=td['time']
  phase=float(re.search(r'sinephase=([\d.]+)',(p/'inputs'/f'{case}.scs').read_text()).group(1))
  points.append(dict(phase_deg=phase,mean_current_a=float(np.trapezoid(td['VO:p'],t)/(t[-1]-t[0]))))
 slope=(points[1]['mean_current_a']-points[0]['mean_current_a'])/(points[1]['phase_deg']-points[0]['phase_deg'])
 fit=dict(points=points,kpd_a_rad=slope*180/np.pi,interpolated_center_deg=points[0]['phase_deg']-points[0]['mean_current_a']/slope)
 (H/'results/safe_gain_fit.json').write_text(json.dumps(fit,indent=2)+'\n')
 for q in [3,5,8]:
  raw=R/'inductor02'/f'tb_rlc_noise_q{q}'/f'tb_rlc_noise_q{q}.raw'
  if not (raw/'pn.pm.pnoise').exists():continue
  pd=parse(raw/'pn.pm.pnoise');fd=parse(raw/'pss.fd.pss');td=parse(raw/'pss.td.pss')
  f=pd['relative frequency'];fosc=float(fd['freq'][1]);peak=float(abs(fd['vp'][1]-fd['vn'][1]));carrier=peak**2/2
  L=pd['out']**2/carrier;parts=components(raw/'pn.pm.pnoise');summed=sum(parts.values())
  err=float(np.max(abs(summed/pd['out']**2-1)));assert err<1e-6
  i=int(np.argmin(abs(np.log(f/1e6))));t=td['time']
  result['vco'].append(dict(q_at_3p3ghz=q,frequency_hz=fosc,carrier_peak_v=peak,phase_noise_1mhz_dbc_hz=float(np.interp(np.log(1e6),np.log(f),10*np.log10(L))),noise_sum_error=err,power_mw=float(-1.2*np.trapezoid(td['VDD:p'],t)/(t[-1]-t[0])*1e3),contributors_at_1mhz=sorted(((k,float(v[i]/summed[i])) for k,v in parts.items()),key=lambda x:-x[1])[:10]))
  spectra[f'q{q}_f']=f;spectra[f'q{q}_L']=L
 means=[]
 for tag in ['lo','center','hi']:
  raw=R/'noise01'/f'tb_joint_timing_{tag}'/f'tb_joint_timing_{tag}.raw'
  if not (raw/'pss.td.pss').exists():continue
  td=parse(raw/'pss.td.pss');t=td['time'];means.append(dict(tag=tag,mean_current_a=float(np.trapezoid(td['VO:p'],t)/(t[-1]-t[0]))))
  if tag=='center' and (raw/'pn.pnoise').exists():
   pd=parse(raw/'pn.pnoise');f=pd['freq'];parts=components(raw/'pn.pnoise');su=sum(parts.values())
   err=float(np.max(abs(su/pd['out']**2-1)));assert err<1e-6
   i=int(np.argmin(abs(np.log(f/1e6))));pulser=sum(v for k,v in parts.items() if k.upper().startswith('XT.'))
   result['sampler_cp'].append(dict(current_asd_1mhz_a_sqrt_hz=float(pd['out'][i]),integrated_current_10k_492m_a=np.sqrt(integral(f,pd['out']**2,1e4,492e6)),noise_sum_error=err,pulser_noise_fraction_1mhz=float(pulser[i]/su[i]) if isinstance(pulser,np.ndarray) else 0,contributors_at_1mhz=sorted(((k,float(v[i]/su[i])) for k,v in parts.items()),key=lambda x:-x[1])[:12]))
   spectra['cp_f']=f;spectra['cp_si']=pd['out']**2
 result['sampler_means']=means
 if len(means)==3:
  gain=(means[2]['mean_current_a']-means[0]['mean_current_a'])/np.deg2rad(.04)
  result['sampler_cp_kpd_a_rad']=gain
  result['sampler_residual_phase_rad']=means[1]['mean_current_a']/gain
  result['sampler_input_referred_asd_1mhz_rad_sqrt_hz']=result['sampler_cp'][0]['current_asd_1mhz_a_sqrt_hz']/abs(gain)
 raw=R/'safe_noise01/tb_joint_safe_center/tb_joint_safe_center.raw'
 if (raw/'pn.pnoise').exists():
  fit=json.loads((H/'results/safe_gain_fit.json').read_text());gain=fit['kpd_a_rad']
  pd=parse(raw/'pn.pnoise');td=parse(raw/'pss.td.pss');f=pd['freq'];t=td['time'];parts=components(raw/'pn.pnoise');su=sum(parts.values())
  assert np.max(abs(su/pd['out']**2-1))<1e-6
  i=int(np.argmin(abs(np.log(f/1e6))));pulse=sum(v for k,v in parts.items() if k.upper().startswith('XT.'))
  mean=float(np.trapezoid(td['VO:p'],t)/(t[-1]-t[0]))
  asd=float(pd['out'][i]);input_asd=asd/abs(gain)
  old=json.loads((H.parent/'transistor_v2/results/noise_summary.json').read_text())
  old_gain=old['matched_detector_operating_point']['kpd_a_rad']
  old_asd=next(x['current_asd_1mhz_a_sqrt_hz'] for x in old['sampler_cp'] if x['case']=='tb_joint_final_center')
  result['safe_sampler_cp']=dict(kpd_a_rad=gain,mean_current_a=mean,linear_residual_phase_rad=mean/gain,phase_deg=fit['interpolated_center_deg'],current_asd_1mhz_a_sqrt_hz=asd,input_referred_asd_1mhz_rad_sqrt_hz=input_asd,gain_ratio_to_ideal_pulser=gain/old_gain,input_noise_asd_ratio_to_ideal_pulser=input_asd/(old_asd/abs(old_gain)),pulser_fraction_1mhz=float(pulse[i]/su[i]),integrated_current_10k_492m_a=np.sqrt(integral(f,pd['out']**2,1e4,492e6)),contributors_at_1mhz=sorted(((k,float(v[i]/su[i])) for k,v in parts.items()),key=lambda x:-x[1])[:12])
  spectra['safe_cp_f']=f;spectra['safe_cp_si']=pd['out']**2
 raw=R/'precision01/tb_rlc_noise_q5_tight/tb_rlc_noise_q5_tight.raw'
 if (raw/'pn.pm.pnoise').exists():
  pd=parse(raw/'pn.pm.pnoise');fd=parse(raw/'pss.fd.pss');f=pd['relative frequency'];L=pd['out']**2/(abs(fd['vp'][1]-fd['vn'][1])**2/2)
  nominal=next(x for x in result['vco'] if x['q_at_3p3ghz']==5);pn1=float(np.interp(np.log(1e6),np.log(f),10*np.log10(L)))
  result['vco_numerical_check']=dict(maxstep_s=2e-12,maxsideband=63,frequency_hz=float(fd['freq'][1]),phase_noise_1mhz_dbc_hz=pn1,frequency_change_relative=float(fd['freq'][1]/nominal['frequency_hz']-1),pn_1mhz_change_db=pn1-nominal['phase_noise_1mhz_dbc_hz'])
 raw=R/'precision_q8/tb_rlc_noise_q8_tight/tb_rlc_noise_q8_tight.raw'
 if (raw/'pn.pm.pnoise').exists():
  pd=parse(raw/'pn.pm.pnoise');fd=parse(raw/'pss.fd.pss');td=parse(raw/'pss.td.pss');f=pd['relative frequency']
  L=pd['out']**2/(abs(fd['vp'][1]-fd['vn'][1])**2/2)
  nominal=next(x for x in result['vco'] if x['q_at_3p3ghz']==8);pn1=float(np.interp(np.log(1e6),np.log(f),10*np.log10(L)))
  result['q8_numerical_check']=dict(maxstep_s=2e-12,maxsideband=63,frequency_hz=float(fd['freq'][1]),phase_noise_1mhz_dbc_hz=pn1,frequency_change_relative=float(fd['freq'][1]/nominal['frequency_hz']-1),pn_1mhz_change_db=pn1-nominal['phase_noise_1mhz_dbc_hz'],steady_vp_range_v=[float(min(td['vp'])),float(max(td['vp']))],steady_vn_range_v=[float(min(td['vn'])),float(max(td['vn']))])
 (H/'results/noise_summary.json').write_text(json.dumps(result,indent=2)+'\n')
 np.savez_compressed(H/'results/noise_spectra.npz',**spectra)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
