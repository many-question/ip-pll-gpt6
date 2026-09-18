from pathlib import Path
import json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
sys.path.insert(0,str(H))
from build_inductor import impedance
R=ROOT/'research/runs/spectre_transistor_v3'
def main():
 p=json.loads((H/'results/inductor_parameters.json').read_text());ns=np.load(H/'results/noise_spectra.npz')
 fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
 f=np.geomspace(.5e9,10e9,500)
 for par in p:
  q=par['q_at_3p3ghz'];z=impedance(f,par['rs_ohm']);axes[0].plot(f/1e9,z.imag/z.real,label=f'RLC: Q(3.3 GHz)={q}')
  axes[1].semilogx(ns[f'q{q}_f'],10*np.log10(ns[f'q{q}_L']),label=f'Q={q}')
 axes[0].plot(f/1e9,2*np.pi*f*2e-9/5,'k--',label='Old 2 nH + 5 ohm')
 axes[0].axvspan(2.688,3.936,color='gray',alpha=.15)
 axes[0].set(xlabel='Frequency (GHz)',ylabel='One-port Q',ylim=(0,15),title='Preliminary inductor model (not PDK)')
 axes[1].set(xlabel='Offset frequency (Hz)',ylabel='SSB phase noise (dBc/Hz)',title='PDK MOS VCO + assumed RLC\nTT, code 0, Vctrl=0.6 V, unloaded')
 for ax in axes:ax.grid(True,alpha=.25);ax.legend()
 fig.savefig(H/'results/inductor_noise.png',dpi=170);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
 for c in ['tt','ss','ff']:
  d=np.load(R/'timing03'/f'tb_cp_timing_{c}'/'waveforms.npz');t=d['time']*1e9
  for ax,lo,hi in [(axes[0],92,100),(axes[1],260,270)]:
   m=(t>=lo)&(t<=hi);ax.plot(t[m],d['pulse'][m],label=c.upper())
 axes[0].axvline(96,color='k',ls='--',label='Enable falls')
 axes[1].axvspan(263,264,color='gray',alpha=.2,label='Reset high')
 axes[0].set(title='Enable change does not truncate pulse',xlabel='Time (ns)',ylabel='CP pulse (V)')
 axes[1].set(title='Reset release cannot re-open pulse',xlabel='Time (ns)',ylabel='CP pulse (V)')
 for ax in axes:ax.grid(True,alpha=.25);ax.legend()
 fig.savefig(H/'results/timing_boundaries.png',dpi=170);plt.close(fig)
 cases=[('inductor_settling','tb_rlc_loaded_c160_settled',160),('inductor_settling','tb_rlc_loaded_c176_settled',176),('inductor_settling192','tb_rlc_loaded_c192_settled',192)]
 fig,ax=plt.subplots(figsize=(8,4.2),layout='constrained')
 for run,case,code in cases:
  p=R/run/case/'waveforms.npz'
  if not p.exists():continue
  d=np.load(p);t=d['time'];v=d['vp']-d['vn'];centers=[];amps=[]
  for lo in np.arange(0,float(t[-1])-10e-9,10e-9):
   mask=(t>=lo)&(t<lo+10e-9)
   if sum(mask)>3:centers.append((lo+5e-9)*1e6);amps.append(np.ptp(v[mask])*1e3)
  ax.semilogy(centers,amps,label=f'Code {code}, 10 mV initial seed')
 ax.set(xlabel='Time (us)',ylabel='Differential peak-to-peak in 10 ns bins (mV)',title='Loaded Q=5 VCO: startup / weak-signal check\nTT, Vctrl=0.6 V, fixed C=60 fF')
 ax.grid(True,alpha=.25);ax.legend()
 fig.savefig(H/'results/loaded_startup.png',dpi=170);plt.close(fig)
if __name__=='__main__':main()
