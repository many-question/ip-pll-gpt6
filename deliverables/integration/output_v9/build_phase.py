"""Swap single CML latch clock polarity; retain the same-phase baseline."""
from analyze import H
import json,datetime
def main():
 for scale in [1,2]:
  p=H/'tb'/f'cml1_opp_s{scale}_tt.scs';assert not p.exists()
  s=(H/'tb'/f'cml1_s{scale}_tt.scs').read_text().replace('XRT (dp dn vp vn out','XRT (dp dn vn vp out')
  p.write_text(s,encoding='utf-8',newline='\n')
 (H/'results/phase_protocol.json').write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),question='Single-latch same phase can track divider transitions; opposite phase should reopen after the raw differential data settled.',change='Swap only RF cp/cn at the retimer port. Raw divider and sizes unchanged.',scope='Compare waveforms and later output noise to establish whether clock-controlled retiming exists; same-phase frequency pass alone is not accepted as retiming.'),indent=2)+'\n')
if __name__=='__main__':main()
