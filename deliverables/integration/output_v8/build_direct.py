"""Remove noise-dominant active mirror; test self-biased AC limiter directly."""
import datetime,json,re
from analyze import H
def main():
 src=(H/'tb/mirror_gain4small_tt.scs').read_text()
 for size,wn,wp in [('small','2u','5u'),('wide','4u','10u')]:
  for pin in ['vp','vn']:
   name=f'direct4_{size}_{pin}_tt';p=H/'tb'/f'{name}.scs';assert not p.exists()
   s=src.replace('include "rf_mirror_gain4small_v8.scs"\n','')
   s=re.sub(r'^XRX .*$',f'XRX ({pin} clk rx_vdd 0) tx_limiter4 wn={wn} wp={wp}',s,flags=re.M)
   s=re.sub(r'^save .*$', 'save vp vn data clk out XRX.g0 XRX.o0 XRX.g1 XRX.o1 XRX.g2 XRX.o2 XRX.g3 XRX.o3 XRT.clkb VDD:p VRX:p VRT:p',s,flags=re.M)
   p.write_text(s,encoding='utf-8',newline='\n')
 protocol=dict(time=datetime.datetime.now().astimezone().isoformat(),basis='Coarse gain4small sampled noise8.406ps is99.922% receiver variance; device PSD sum matches total. Mirror front-end dominates. Fine result still pending.',
  hypothesis='AC-couple the tank waveform directly into the self-biased4-stage inverter limiter, removing the active-mirror front-end noise and pole. Original three-stage DC-connected chain failed; this topology recenters each stage independently.',
  conditions='UnchangedTT27,1.2V,noiseless ideal3.936GHz RF replay,physical/4divider,scale2retimer/oscale4,10fF. Four combinations of width and polarity, original functional acceptance unchanged.',
  scope='Functional diagnosis, no noise claim or adoption. Changed RF loading must be tested with actual VCO after screening.')
 (H/'results/direct_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
if __name__=='__main__':main()
