"""Plot measured waveforms with coherent RF phase and sampled noise spectra."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H,R,cross
def main():
 v=json.loads((H/'results/validation.json').read_text());by={r['case']:r for r in v};dest=H/'figures';dest.mkdir(exist_ok=True)
 cases=['cml1_s1_tt','cml1_opp_s1_tt','cml2_s2_tt','cml2_opp_s2_tt'];fig,ax=plt.subplots(len(cases),1,figsize=(10,9),sharex=True,constrained_layout=True)
 events=[]
 for row,name in zip(ax,cases):
  r=by[name];p=R/r['run']/name/'waveforms.npz';start=96/984e6;end=start+1/984e6
  with np.load(p) as z:
   keep=(z['time']>=start)&(z['time']<=end);t=z['time'][keep];x=(t-start)*1e9
   for label,y in [('raw data',z['dp'][keep]-z['dn'][keep]),('retimed',z['XRT.qp'][keep]-z['XRT.qn'][keep]),('local clock',z['XRT.ckp'][keep]-z['XRT.ckn'][keep])]:
    row.plot(x,y,label=label);events.append(dict(case=name,signal=label,rise_time_ps=((cross(t,y)-start)*1e12).tolist(),fall_time_ps=((cross(t,-y)-start)*1e12).tolist(),range_v=[float(min(y)),float(max(y))]))
  row.set(ylabel='Differential V',title=name);row.axhline(0,color='gray',lw=.5);row.grid(alpha=.2)
 ax[0].legend(loc='upper right');ax[-1].set(xlabel='Time within one output period (ns)')
 fig.suptitle('TT27, 1.2 V, actual raw divider + retimer; ideal noiseless RF3.936GHz')
 fig.savefig(dest/'cml_phase_waveforms.png',dpi=170);plt.close(fig)
 (H/'results/waveform_events.json').write_text(json.dumps(events,indent=2)+'\n')
 p=H/'results/noise_validation.json'
 if not p.exists():return
 n=json.loads(p.read_text());z=np.load(H/'results/noise_spectra.npz');fig,ax=plt.subplots(figsize=(10,5),constrained_layout=True)
 for r in n['cases']:
  if not r.get('valid_noise'):continue
  key=r['case'];ax.loglog(z[key+'_f'],np.sqrt(z[key+'_st'])*1e15,label=key.removeprefix('noise_')+f" : {r['numeric_jitter_fs']:.1f} fs")
 ax.set(xlabel='Offset frequency (Hz)',ylabel='Edge-time ASD (fs/sqrt(Hz))',title='Sampled output noise, explicit10kHz-492MHz integral; TT27')
 ax.legend(fontsize=8);ax.grid(alpha=.2,which='both');fig.savefig(dest/'noise_comparison.png',dpi=170);plt.close(fig)
 a='noise_cml2_s2_coarse';b='noise_cml2_s2_fine'
 if a+'_f' in z and b+'_f' in z:
  assert np.allclose(z[a+'_f'],z[b+'_f'],rtol=1e-10,atol=0)
  fig,ax=plt.subplots(2,1,figsize=(9,6.2),sharex=True,constrained_layout=True)
  for key,label,style in [(a,'1 ps / 63 harmonics / 63 colored sidebands','-'),(b,'0.5 ps / 127 / 127','--')]:ax[0].loglog(z[key+'_f'],np.sqrt(z[key+'_st'])*1e15,style,label=label)
  ax[0].set(ylabel='Edge-time ASD (fs/sqrt(Hz))',title='Original-polarity two-stage CML: joint numerical refinement');ax[0].legend(fontsize=8)
  ax[1].semilogx(z[a+'_f'],10*np.log10(z[b+'_st']/z[a+'_st']));ax[1].axhline(.1,color='gray',ls=':');ax[1].axhline(-.1,color='gray',ls=':')
  ax[1].set(xlabel='Offset frequency (Hz)',ylabel='Fine / coarse PSD (dB)')
  for row in ax:row.grid(alpha=.2,which='both')
  fig.savefig(dest/'precision_comparison.png',dpi=170);plt.close(fig)
if __name__=='__main__':main()
