"""Matched isolated-divider additive noise and predeclared precision check."""
import json,re
from analyze import H

def main():
 for variant in ['base','clamp']:
  original=(H/'tb'/f'divider_{variant}_pss.scs').read_text()
  for step,sb in [(2,31),(1,63)]:
   body=re.sub(r'^pss pss.*$',f'pss pss fund=984M harms={sb} tstab=200n maxstep={step}p method=traponly errpreset=conservative maxperiods=20 saveinit=yes writefinal="__FINAL_STATE__"',original,flags=re.M)
   body+=f'pn pnoise start=10k stop=492M dec=30 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] maxsideband={sb}\nedge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]\n'
   dest=H/'tb'/f'noise_divider_{variant}_{step}ps.scs';assert not dest.exists();dest.write_text(body,encoding='utf-8',newline='\n')
 spec=dict(scope='Isolated divider intrinsic rising-edge jitter, ideal noiseless measured-shape RF3.936GHz, TT27,1.2V,10fF, output984MHz,10kHz..492MHz; no actual VCO source impedance/noise or retimer.',precision_limits=dict(max_relative_integrated_jitter_change=.01,max_spectrum_delta_db=.1,numeric_vs_spectre_jee_relative=.015),comparison='2ps/31 harmonics/31 sidebands versus1ps/63 harmonics/63 sidebands. Joint precision study, not independent attribution of each setting. Both must have valid984MHz periodic waveform with4RF/1output edges and endpoint mismatch<1mV.')
 (H/'results/divider_noise_protocol.json').write_text(json.dumps(spec,indent=2)+'\n')

if __name__=='__main__':main()
