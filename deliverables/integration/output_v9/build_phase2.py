"""Check the opposite RF polarity for the two-latch retimer; no ideal delay."""
from analyze import H
import json,datetime

def main():
 for source,dest in [('cml2_s2_tt','cml2_opp_s2_tt'),('cml2_regen_b_tt','cml2_regen_bopp_tt'),('cml2_regen_c_tt','cml2_regen_copp_tt')]:
  p=H/'tb'/f'{dest}.scs';assert not p.exists()
  s=(H/'tb'/f'{source}.scs').read_text().replace('XRT (dp dn vp vn out','XRT (dp dn vn vp out')
  p.write_text(s,encoding='utf-8',newline='\n')
 (H/'results/phase2_protocol.json').write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),question='Two-stage original polarity: raw data zero crossing occurs close to the master clock closing. Does swapping both clock polarities improve settled-data margin and reject divider timing noise?',change='Swap only RF cp/cn at the retimer port. No ideal phase shifter or change to physical divider; retain original-polarity controls.',scope='Hypothesis from measured TT waveforms. Function, finite timing sensitivity, actual device noise, and numerical refinement must be checked separately; no PVT or architecture adoption.'),indent=2)+'\n')

if __name__=='__main__':main()
