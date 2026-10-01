"""Use differential regeneration at output frequency, after CML retiming."""
import datetime,json,re
from analyze import H
def main():
 B=H.parents[1]/'blocks/output_v9'
 p=B/'cml_retimer_regen_v9.scs';assert not p.exists()
 s=(B/'cml_retimer2_v9.scs').read_text().replace('tx_cml_retimer2_v9','tx_cml_retimer_regen_v9').replace('cdec=10p','cdec=10p rwn=4u rwp=600n ribias=10u')
 s=re.sub(r'^XL .*$', 'XL (qp qn out outn vdd vss) tx_regen_receiver wn=rwn wp=rwp ibias=ribias cc=240f\nCNLOAD (outn vss) capacitor c=10f',s,flags=re.M)
 p.write_text(s,encoding='utf-8',newline='\n')
 for tag,sc,wn,wp,ib in [('a',1,'4u','600n','10u'),('b',1,'8u','1.2u','20u'),('c',2,'8u','1.2u','20u')]:
  p=H/'tb'/f'cml2_regen_{tag}_tt.scs';assert not p.exists()
  s=(H/'tb/cml2_s1_tt.scs').read_text().replace('include "cml_retimer2_v9.scs"','include "receiver.scs"\ninclude "cml_retimer_regen_v9.scs"')
  s=s.replace('tx_cml_retimer2_v9 scale=1 lscale=1',f'tx_cml_retimer_regen_v9 scale={sc} rwn={wn} rwp={wp} ribias={ib}')
  s=s.replace('XRT.qp XRT.qn','XRT.qp XRT.qn XRT.XL.gp XRT.XL.gn XRT.XL.qp XRT.XL.qn')
  p.write_text(s,encoding='utf-8',newline='\n')
 (H/'results/regen_output_protocol.json').write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),basis='Single CML same phase passes only about0.5x deterministic timing suppression and~978fs coarse noise; opposite phase about2x sensitivity and~2558fs. Both are rejected as final choices. Two-latch physical baseline function passes.',
  hypothesis='Differential post-retiming regeneration at984MHz may avoid the four-stage AC chain and reject common-mode latch/bias fluctuations. Existing RF regenerative receiver failed at3.936GHz; its behavior at984MHz is a new experiment, not inherited validation.',
  change='Replace single-ended tx_limiter4 only with actual tx_regen_receiver using both retimed nodes; dummy complementary output10fF balances load. Compare three stated receiver/latch scalings.',conditions='Same actual raw divider,ideal noiseless RFshape,TT27/1.2V/10fF,original CML output frequency/swing checks. Actual VCO and mainloop excluded.'),indent=2)+'\n')
if __name__=='__main__':main()
