"""Noise on the first output chain that meets the original TT waveform screen."""
import datetime,json,re
from analyze import H
def main():
 rows=json.loads((H/'results/validation.json').read_text());picked=next(x for x in rows if x['case']=='mirror_gain4small_tt')
 assert picked['transient']['pass_function']
 src=(H/'tb/mirror_gain4small_tt.scs').read_text()
 for tag,step,harms in [('1ps','1p',63),('halfps','500f',127)]:
  name='noise_gain4small_'+tag;p=H/'tb'/f'{name}.scs';assert not p.exists()
  s=re.sub(r'^tran tran.*$',f'pss pss fund=984M harms={harms} tstab=200n maxstep={step} method=traponly errpreset=conservative maxperiods=30 saveinit=yes writefinal="__FINAL_STATE__"',src,flags=re.M)
  s+=f'''pn pnoise start=10k stop=492M dec=30 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=1 maxsideband={harms}
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
save XRF:vp_vss_flow XRF:vn_vss_flow
'''
  p.write_text(s,encoding='utf-8',newline='\n')
 protocol=dict(time=datetime.datetime.now().astimezone().isoformat(),selection='mirror_gain4small_tt passes original TT frequency/swing screen and uses less power than standard-width gain4. This is a provisional fixture candidate, not architecture adoption.',
  conditions='TT27,1.2V,ideal noiseless prior RF shape3.936GHz,/4 physical clamped divider,new40uA mirror receiver and4 half-width self-biased gain stages,physical C2MOS scale2/output scale4,10fF. All output-chain devices active; actual VCO/mainloop/FLL/generators absent.',
  band_hz=[1e4,492e6],periodic_fund_hz=984e6,sampleratio=1,event='out rising0.6V',
  precision_limits=dict(relative_integrated_jitter=.01,max_spectrum_delta_db=.1,numeric_vs_jee=.015),
  refinement='1ps/63harmonics/63maxsideband to0.5ps/127/127, joint time/bandwidth refinement, same dec30 frequency grid. maxsideband is for colored sources in fullspectrum.',
  acceptance='Require PSS success and independent1 output/1 data/4 clock cycles, dominant output1/clock4, logic swing, endpoint mismatch<1mV, explicit band integral and convergence. Even<200fs here is not fullPLL signoff.',
  power='VDD total simultaneously covers divider,receiver,retimer andbuffer; subbranch currents separate receiver/retimer. Ideal RF source real/reactive loading is not actual VCO supply power.')
 (H/'results/noise_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
if __name__=='__main__':main()
