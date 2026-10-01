"""One physical module change per candidate, only after gating is confirmed."""
from pathlib import Path
import json,re,datetime
from analyze import H

def main():
 gate=json.loads((H/'results/gating_validation.json').read_text());assert gate['pass_gating']
 d=H.parents[1];b=d/'blocks/noise_v10';v9=d/'blocks/output_v9';old=H.parent/'output_v9'
 specs={
  'divlast2':dict(group='divider',change='Double scale of only selected/4 final slave XS2_1: device widths/current double and Rload halves; all other divider/retimer/output parameters unchanged.',hypothesis='Reduce dominant final-slave load-resistor/device noise and improve drive into existing TG/retimer load; verify added internal load and power.'),
  'master2':dict(group='master',change='Double only XRT.XM scale, preserving slave/output/bias reference.',hypothesis='Reduce dominant master resistor/device contribution at actual downstream load; check extra input loading and power.'),
  'slave2':dict(group='slave',change='Double only XRT.XS scale, preserving master/output/bias reference.',hypothesis='Reduce slave RP/MT/device noise and output source resistance; check increased master loading and power.'),
  'bias1p':dict(group='bias',change='Add1pF at the existing retimer current-mirror reference gate nb; no new bias generator.',hypothesis='Filter mirror gate noise/coupling without changing DC current; check startup, area burden and module noise.'),
  'outfirst2':dict(group='output',change='Double only first output-restoring inverter XRT.XL.X0 widths; retain all remaining stages, feedbackR and couplingC.',hypothesis='Reduce dominant first-inverter input-referred device noise; retain actual slave loading to expose adverse effects.'),
  'out2stage':dict(group='output',change='Replace four AC-coupled restoring inverters plus final inverter with two AC-coupled inverters plus identical final inverter; same first-stage sizes/R/C.',hypothesis='Remove later-stage noise/power at984MHz while preserving correct output swing and frequency.')}
 base=(old/'tb/cml2_s2_tt.scs').read_text();ret=(v9/'cml_retimer2_v9.scs').read_text();variants={}
 for name,info in specs.items():
  case='opt_'+name+'_tt';s=base;dest=H/'tb'/f'{case}.scs';assert not dest.exists()
  if name=='divlast2':
   mod='tx_divider_raw_v10_last2';block='divider_v10_last2.scs';q=(v9/'divider_raw_v9.scs').read_text().replace('tx_divider_raw_v9',mod)
   q=re.sub(r'^(XS2_1 .*?)scale=scale2',r'\g<1>scale=2*scale2',q,flags=re.M)
   s=s.replace('divider_raw_v9.scs',block).replace('tx_divider_raw_v9',mod)
  else:
   mod='tx_cml_v10_'+name;block='cml_v10_'+name+'.scs';q=ret.replace('tx_cml_retimer2_v9',mod)
   if name in ['master2','slave2']:
    inst='XM' if name=='master2' else 'XS';q=re.sub(r'^('+inst+r' .*?)scale=scale',r'\g<1>scale=2*scale',q,flags=re.M)
   elif name=='bias1p':q=q.replace('IREF (','CNB (nb vss) capacitor c=1p\nIREF (')
   elif name=='outfirst2':
    limiter=(d/'blocks/transistor_v2/limiter_chain.scs').read_text();limiter=re.search(r'subckt tx_limiter4 .*?ends tx_limiter4',limiter,re.S)[0]
    limiter=limiter.replace('tx_limiter4','tx_limiter4_first2_v10').replace('X0 (g0 o0 vdd vss) pll_inv wn=wn wp=wp','X0 (g0 o0 vdd vss) pll_inv wn=2*wn wp=2*wp')
    q='simulator lang=spectre\n'+limiter+'\n'+q.replace('tx_limiter4 wn=','tx_limiter4_first2_v10 wn=')
   elif name=='out2stage':q=q.replace('tx_limiter4 wn=','tx_limiter2 wn=')
   s=s.replace('cml_retimer2_v9.scs',block).replace('tx_cml_retimer2_v9',mod)
  bp=b/block;assert not bp.exists();bp.write_text(q,encoding='utf-8',newline='\n')
  s=s.replace('save vp vn','save XRT.mp XRT.mn XRT.XL.g0 XRT.XL.o0 vp vn')
  dest.write_text(s,encoding='utf-8',newline='\n');variants[case]=info
 proto=dict(time=datetime.datetime.now().astimezone().isoformat(),gating_prerequisite='All seven authoritative gating cases pass; legacy mixed-option trials excluded.',variants=variants,
  sequence='Transient function first, then selected-module-only noise at actual full-chain loading, then all-on noise for useful candidates. Do not rank by only-noise result alone.',
  selection='Exploratory goal: >=5% reduction in selected module RMS, retain original frequency/swing criteria; report power delta. This is an internal screening target, not a changed user specification. WholePLL<=4mW remains required and unverified.',
  conditions='Same TT27/1.2V/984MHz/10fF ideal noiseless RF fixture and PSS1ps/63. Candidate refinement must be newly performed before numerical qualification.')
 (H/'results/optimization_protocol.json').write_text(json.dumps(proto,indent=2)+'\n');print(list(variants))

if __name__=='__main__':main()
