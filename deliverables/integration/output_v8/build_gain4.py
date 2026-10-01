import json,datetime
from analyze import H
def main():
 b=H.parents[1]/'blocks/output_v8'
 for tag,wn,wp in [('gain4','4u','10u'),('gain4small','2u','5u')]:
  sub='tx_rf_mirror_'+tag+'_v8';p=b/('rf_mirror_'+tag+'_v8.scs');assert not p.exists()
  s=(b/'rf_mirror_gain3_v8.scs').read_text().replace('tx_rf_mirror_gain3_v8',sub).replace('tx_limiter3 wn=4u wp=10u',f'tx_limiter4 wn={wn} wp={wp}')
  p.write_text(s,encoding='utf-8',newline='\n')
  tb=H/'tb'/f'mirror_{tag}_tt.scs';assert not tb.exists()
  s=(H/'tb/mirror_gain3_tt.scs').read_text().replace('rf_mirror_gain3_v8.scs',p.name).replace('tx_rf_mirror_gain3_v8',sub)
  tb.write_text(s,encoding='utf-8',newline='\n')
 r=dict(time=datetime.datetime.now().astimezone().isoformat(),reason='Mirror+3 self-biased stages restores984MHz output but clock max0.964V is below the original1.0V clock-swing screen. Add one RF gain stage; compare standard and half-width limiting chains.',
  criteria='Original protocol frequency/period/swing criteria remain. The later-added89ps sample check was found to precede propagation and is retained only as a diagnostic; it was never in the predeclared protocol. Actual data/output edge delays are now reported. No claim of data-independent retiming or jitter suppression.')
 (H/'results/gain4_protocol.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
