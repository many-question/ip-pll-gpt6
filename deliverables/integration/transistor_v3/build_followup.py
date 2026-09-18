from pathlib import Path
import json,re
H=Path(__file__).resolve().parent
def main():
 # Confirm low-Q startup failure with 1000x seed and smaller trap timestep.
 for q in [3,5]:
  s=(H/'tb'/f'tb_rlc_q{q}_c255_nom.scs').read_text()
  s=s.replace('vp=1.20001','vp=1.21').replace('maxstep=5p','maxstep=2p method=trap')
  (H/'tb'/f'tb_rlc_q{q}_c255_seedcheck.scs').write_text(s)
 # Diagnostic design perturbations at unchanged Q=5; not adopted silently.
 s=(H/'tb/tb_rlc_q5_c255_nom.scs').read_text()
 for tag,param in [('wide','core_w=80u'),('current','ibias=120u')]:
  t=s.replace('cscale=1','cscale=1 '+param).replace('vp=1.20001','vp=1.21')
  (H/'tb'/f'tb_rlc_q5_c255_{tag}.scs').write_text(t)
 # Loaded VCO endpoints with actual sampler, CP pulser, divider and load.
 rs=json.loads((H/'results/inductor_parameters.json').read_text())[1]['rs_ohm']
 for code in [0,255]:
  for voltage in ['lo','hi']:
   s=(H.parent/'transistor_v2/tb'/f'tb_loaded_final_c{code}_{voltage}_light60.scs').read_text()
   s=s.replace('lc_vco_candidate.scs','lc_vco_rlc.scs').replace('tx_lc_vco_candidate fixed_c=60f',f'tx_lc_vco_rlc fixed_c=60f series_r={rs}')
   s=s.replace('ahdl_include "sampler_interface.va"','include "digital_cells_v2.scs"\ninclude "cp_timing.scs"')
   s=s.replace('XA (refb hp hn sample held pulse vdd 0) sampler_interface','XA (refb en rst pulse vdd 0) tx_cp_timing')
   s=s.replace('stop=200n errpreset=moderate maxstep=5p','stop=300n errpreset=conservative maxstep=5p')
   (H/'tb'/f'tb_rlc_loaded_c{code}_{voltage}.scs').write_text(s)
 # Tighter digital accuracy cross-check includes valid/invalid and retune.
 for stem in ['tb_config_tt','tb_supervisor_tt']:
  s=(H/'tb'/f'{stem}.scs').read_text().replace('reltol=1e-3','reltol=1e-4').replace('vabstol=1e-5','vabstol=1e-6')
  if stem=='tb_config_tt':
   # Original first 12 slots include invalid 0..8 and valid 9..11.
   s=s.replace('stop=72.5u','stop=12.5u')
  (H/'tb'/f'{stem}_tight.scs').write_text(s)
 s=(H/'tb/tb_rlc_noise_q5.scs').read_text().replace('maxstep=5p','maxstep=2p').replace('maxsideband=31','maxsideband=63')
 (H/'tb/tb_rlc_noise_q5_tight.scs').write_text(s)
if __name__=='__main__':main()
