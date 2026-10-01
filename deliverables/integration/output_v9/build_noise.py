"""Create noise TBs only for a named, waveform-passing transistor fixture."""
import argparse,datetime,json,re
from analyze import H
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--tag',default='coarse',choices=['coarse','fine']);a=p.parse_args()
 rows=json.loads((H/'results/validation.json').read_text());r=next(x for x in rows if x['case']==a.case);assert r['transient']['pass_function']
 name='noise_'+a.case.removesuffix('_tt')+'_'+a.tag;dest=H/'tb'/f'{name}.scs';assert not dest.exists()
 step,harms=('1p',63) if a.tag=='coarse' else ('500f',127)
 s=(H/'tb'/f'{a.case}.scs').read_text()
 s=re.sub(r'^tran tran.*$',f'pss pss fund=984M harms={harms} tstab=200n maxstep={step} method=traponly errpreset=conservative maxperiods=30 saveinit=yes writefinal="__FINAL_STATE__"',s,flags=re.M)
 s+=f'''pn pnoise start=10k stop=492M dec=30 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=1 maxsideband={harms}
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
'''
 dest.write_text(s,encoding='utf-8',newline='\n')
 (H/'results'/f'{name}_protocol.json').write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),source=a.case,case=name,selection='Passed predeclared TT waveform screen only; not accepted as low-noise design.',conditions='TT27,1.2V,ideal noiseless measuredshape RF3.936G,/4,10fF,actual raw divider and CML retimer chain; VCO/mainloop/FLL/generators absent.',analysis=f'984MHz PSS,{step}maxstep,{harms}harmonics/{harms}colorednoise sidebands;sampled output rising0.6V,ratio1,10kHz–492MHz; all device noise.',scope='Explicit ASD²/slew² integration plus Jee; independent periodic count,dominant harmonics,logic rails,endpoint mismatch. Joint refinement is required before noise is numerically qualified.'),indent=2)+'\n')
 print(name)
if __name__=='__main__':main()
