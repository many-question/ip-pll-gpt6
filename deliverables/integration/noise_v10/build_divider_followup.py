"""Two focused divider follow-ups prompted by the failed last-slave scaling."""
import datetime,json,re
from analyze import H

def main():
 p=H/'results/optimization_protocol.json';proto=json.loads(p.read_text());n=json.loads((H/'results/noise_validation.json').read_text())
 prior=next(r for r in n['cases'] if r['case']=='noise_opt_divlast2_only_coarse')
 assert prior['valid_noise'] and prior['numeric_jitter_fs']>700
 b=H.parents[1]/'blocks';base=(H/'tb/opt_divlast2_tt.scs').read_text();old=(b/'output_v9/divider_raw_v9.scs').read_text()
 plans={
  'divlasthalf':dict(change='Halve only selected/4 final slave XS2_1 scale from1 to0.5; remaining divider,retimer and output unchanged.',hypothesis='The doubled last slave raised preceding master contribution from151.8 to466.2fs and both TG contributions; test reduced upstream loading and altered settling with lower current, without assuming noise scales monotonically.'),
  'divtg4':dict(change='Only selected/4 differential output selection TGs XO2/XON2 use WN4um/WP8um instead of1um/2um. L,divider latches,retimer and output unchanged.',hypothesis='Target measured114.5/112.7fs selection-TG contributions and data-path resistance while retaining baseline last-slave sizing; validate added parasitic loading.')}
 for name,info in plans.items():
  mod='tx_divider_v10_'+name;filename='divider_v10_'+name+'.scs';q=old.replace('tx_divider_raw_v9',mod)
  if name=='divlasthalf':q=re.sub(r'^(XS2_1 .*?)scale=scale2',r'\g<1>scale=0.5*scale2',q,flags=re.M)
  else:q=re.sub(r'^(XO[N]?2 .*?)wn=1u wp=2u',r'\g<1>wn=4u wp=8u',q,flags=re.M)
  bp=b/'noise_v10'/filename;assert not bp.exists();bp.write_text(q,encoding='utf-8',newline='\n')
  case='opt_'+name+'_tt';tb=H/'tb'/f'{case}.scs';assert not tb.exists()
  tb.write_text(base.replace('divider_v10_last2.scs',filename).replace('tx_divider_raw_v10_last2',mod),encoding='utf-8',newline='\n')
  proto['variants'][case]=dict(group='divider',**info,followup_declared=datetime.datetime.now().astimezone().isoformat(),prompting_evidence='noise_opt_divlast2_only_coarse plus baseline device decomposition; no criteria changed')
 p.write_text(json.dumps(proto,indent=2)+'\n');print(list(plans))

if __name__=='__main__':main()
