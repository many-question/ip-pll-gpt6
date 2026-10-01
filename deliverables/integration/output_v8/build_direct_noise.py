"""Exploratory noise of the direct4 wide candidate after original function passes."""
import datetime,json,re
from analyze import H
def main():
 rows=json.loads((H/'results/validation.json').read_text())
 assert next(x for x in rows if x['case']=='direct4_wide_vp_tt')['transient']['pass_function']
 p=H/'tb/noise_direct4wide_1ps.scs';assert not p.exists()
 s=(H/'tb/direct4_wide_vp_tt.scs').read_text()
 s=re.sub(r'^tran tran.*$', 'pss pss fund=984M harms=63 tstab=200n maxstep=1p method=traponly errpreset=conservative maxperiods=30 saveinit=yes writefinal="__FINAL_STATE__"',s,flags=re.M)
 s+='''pn pnoise start=10k stop=492M dec=30 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=1 maxsideband=63
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
'''
 p.write_text(s,encoding='utf-8',newline='\n')
 protocol=dict(time=datetime.datetime.now().astimezone().isoformat(),case='noise_direct4wide_1ps',selection='direct4_wide_vp_tt passes unchanged original function criteria. Small widths fail clock rails and are not selected.',
  scope='Exploratory single-point noise of direct4 wn4u/wp10u, finaldriver2x, actualscale2C2MOS. IdealnoiselessRF3.936G/TT27/1.2V/10fF. Same band,periodic/integration checks as noise_protocol.json; no refinement or200fs signoff from this single run.',
  purpose='Test whether removing the noise-dominant mirror front-end improves integrated noise while driving the actual clock load; do not claim isolated topology comparison because limiter widths also double.')
 (H/'results/direct_noise_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
if __name__=='__main__':main()
