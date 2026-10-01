"""Build selected-only or all-on noise TB after the candidate passes function."""
import argparse,json,re,datetime
from analyze import H

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--mode',choices=['only','all'],required=True);p.add_argument('--tag',choices=['coarse','fine'],default='coarse');a=p.parse_args()
 v=json.loads((H/'results/validation.json').read_text());r=next(x for x in v if x['case']==a.case);assert r['transient']['pass_function']
 proto=json.loads((H/'results/optimization_protocol.json').read_text());info=proto['variants'][a.case]
 gate=json.loads((H/'results/gating_protocol.json').read_text());paths=gate['boundaries'][info['group']] if a.mode=='only' else sum(gate['boundaries'].values(),[])
 case='noise_'+a.case.removesuffix('_tt')+'_'+a.mode+'_'+a.tag;dest=H/'tb'/f'{case}.scs';assert not dest.exists()
 s=(H/'tb'/f'{a.case}.scs').read_text().replace('temp=27','temp=27 noiseon_inst=['+' '.join(paths)+'] noiseon_type=all')
 step,nh=('1p',63) if a.tag=='coarse' else ('500f',127)
 s=re.sub(r'^tran tran.*$',f'pss pss fund=984M harms={nh} tstab=200n maxstep={step} method=traponly errpreset=conservative maxperiods=30 saveinit=yes writefinal="__FINAL_STATE__"',s,flags=re.M)
 s+=f'pn pnoise start=10k stop=492M dec=30 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=1 maxsideband={nh}\nedge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]\n'
 dest.write_text(s,encoding='utf-8',newline='\n')
 (H/'results'/f'{case}_protocol.json').write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),case=case,source=a.case,group=info['group'],noise_mode=a.mode,on=paths,qualification='Passed transient function only; must independently verify periodic orbit,noise routing,integration and numerical precision.'),indent=2)+'\n');print(case)

if __name__=='__main__':main()
