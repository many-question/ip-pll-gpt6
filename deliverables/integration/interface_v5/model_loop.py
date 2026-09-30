"""Measured-gain loop screen; never label this complete PLL noise validation."""
import sys,json
import numpy as np
from analyze import H,R,cross,measure
sys.path.insert(0,str(H.parents[1]/'architecture/behavioral_v1'))
from model import Loop,continuous_open,sampled_matrices
sys.path.insert(0,str(H.parent/'transistor_v2'))
from analyze_noise import parse

def main():
 pts=json.loads((H/'results/gain_points.json').read_text())
 pts=sorted([p for p in pts if p['run']=='gain84_fine'],key=lambda p:p['phase_deg']);assert len(pts)==3
 deg=np.array([p['phase_deg'] for p in pts]);current=np.array([p['mean_clamp_current_a'] for p in pts]);coef=np.polyfit(np.deg2rad(deg),current,1)
 kpd=-float(coef[0]);zero=float(-coef[1]/coef[0]*180/np.pi)
 assert kpd>0 and current[0]*current[-1]<0
 job=R/pts[1]['run']/pts[1]['case'];td=parse(job/(job.name+'.raw')/'pss.td.pss');t=td['time'];period=t[-1]-t[0]
 rp=cross(t,td['refb'],.6)[0];pp=cross(t,td['pulse'],.6)[0];pf=cross(t,-td['pulse'],-.6)[0]
 duty=float(((pf-pp)%period)/period);delay=float(((pp-rp)%period)/period)
 cal=[]
 p=R/'calibration_local/cal_local'
 for i,v in enumerate([.80,.82,.84,.86]):
  row=measure(p,((i*180+60)*1e-9,(i+1)*180e-9));row['control_v']=v;cal.append(row)
 (H/'results/calibration_local.json').write_text(json.dumps(cal,indent=2)+'\n')
 kv=float((cal[3]['f_ghz']-cal[1]['f_ghz'])*1e9/.04)
 slopes=[float((b['f_ghz']-a['f_ghz'])*1e9/.02) for a,b in zip(cal,cal[1:])]
 rows=[]
 for name,r,cscale in [('original',100e3,1),('r50k',50e3,1),('fast',100e3,.25)]:
  lp=Loop(24e6,kpd,2*np.pi*kv,r,28.6478897565412e-12*cscale,1.90985931710274e-12*cscale,duty,delay)
  eig=np.linalg.eigvals(sampled_matrices(lp)[0]);rho=float(max(abs(eig)))
  f=np.geomspace(1e3,12e6,20000);g=continuous_open(lp,f);i=np.argmin(abs(np.log(abs(g))))
  rows.append(dict(name=name,r_ohm=r,c1_f=lp.c1,c2_f=lp.c2,crossover_hz=float(f[i]),continuous_phase_margin_deg=float(180+np.angle(g[i],deg=True)),sampled_spectral_radius=rho,slow_time_constant_s=float(-1/lp.fs/np.log(rho)) if rho<1 else None))
 out=dict(kpd_a_per_rad=kpd,zero_current_phase_deg=zero,clamp_v=.84,fit_max_error_a=float(max(abs(np.polyval(coef,np.deg2rad(deg))-current))),pulse_duty=duty,pulse_delay_cycles=delay,kvco_hz_per_v=kv,local_interval_slopes_hz_per_v=slopes,loops=rows,limitations=['Detector fixture uses measured RF shape as an ideal voltage source; no VCO source impedance or noise back-action.','Kvco is a local secant with periodic sampling and finite windows; phase-dependent pulling is not captured by this scalar gain.','Filter elements are schematic ideal R/C; sampled linear model is a design screen, not nonlinear capture or jitter signoff.'])
 (H/'results/loop_model.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
