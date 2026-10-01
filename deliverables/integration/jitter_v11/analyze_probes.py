"""Device headroom and internal voltage slopes on settled physical CML chains."""
import json
import numpy as np
from analyze import H,R,ROOT,parse,cross,wavecheck

def mean(t,v):return float(np.trapezoid(v,t)/(t[-1]-t[0]))
def stats(t,v):return dict(min=float(min(v)),max=float(max(v)),mean=mean(t,v))
def slopes(t,v,lev):
 i=np.flatnonzero((v[:-1]<lev)&(v[1:]>=lev))
 return [(v[j+1]-v[j])/(t[j+1]-t[j])*1e-9 for j in i]
def run():
 rows=[]
 for name in ['probe_base_settled','probe_outfirst2_settled']:
  p=R/'probe_settled'/name
  rec=json.loads((p/'result.json').read_text());assert rec['ok'] and rec['remote_inputs_match']
  with np.load(p/'waveforms.npz') as z:d=dict(z)
  row=dict(case=name,function=wavecheck(d,name));assert row['function']['pass_function']
  # Integrate an exact integer number of output periods.
  t=np.linspace(d['time'][-1]-3/984e6,d['time'][-1],12289);d={k:np.interp(t,d['time'],v) for k,v in d.items() if k!='time' and v.shape==d['time'].shape}
  row['voltage']={k:dict(range_v=[float(min(d[k])),float(max(d[k]))],rising_slopes_at_midrange_v_per_ns=list(map(float,slopes(t,d[k],(max(d[k])+min(d[k]))/2)))) for k in ['dp','XRT.qp','XRT.XL.g0','XRT.XL.o0','out']}
  row['differential']={}
  for tag,a,b in [('divider','dp','dn'),('retimed','XRT.qp','XRT.qn'),('divider_clock','XD.ckp2','XD.ckn2'),('retimer_clock','XRT.ckp','XRT.ckn')]:
   v=d[a]-d[b];row['differential'][tag]=dict(range_v=[float(min(v)),float(max(v))],zero_cross_slopes_v_per_ns=list(map(float,slopes(t,v,0))))
  row['latches']={}
  for l in ['XD.XM2_0','XD.XS2_0','XD.XM2_1','XD.XS2_1','XRT.XM','XRT.XS']:
   di={};row['latches'][l]=di
   for m in ['MT','MCS','MCH','MDP','MDN','MHP','MHN']:
    v=lambda k:d[l+'.'+m+':'+k]
    ids=v('ids');margin=v('vds')-v('vdsat');active=ids>.1*max(ids)
    di[m]=dict(ids_uA=stats(t,ids*1e6),vds_v=stats(t,v('vds')),vdsat_v=stats(t,v('vdsat')),saturation_margin_v=stats(t,margin),fraction_negative_margin_when_active=mean(t,(active&(margin<0)).astype(float))/max(mean(t,active.astype(float)),1e-20))
   cs=d[l+'.MCS:ids'];ch=d[l+'.MCH:ids'];fraction=cs/(cs+ch)
   di['sample_current_fraction']=stats(t,fraction)
   di['fraction_time_sample_and_hold_both_above_10_percent']=mean(t,((fraction>.1)&(fraction<.9)).astype(float))
  # Compare observed physical output to the predecessor transient, same absolute phase.
  old='opt_outfirst2_tt' if 'outfirst2' in name else 'opt_base_tt'
  candidates=list((ROOT/'research/runs/spectre_noise_v10').glob('*/'+old+'/waveforms.npz'))
  if candidates:
   with np.load(candidates[0]) as z:
    u=np.interp(t,z['time'],z['out']);row['reference_output_max_error_v']=float(max(abs(u-d['out'])))
  row['exact_window_power_mw']={k:mean(t,-1.2*d[k]*1e3) for k in ['VDD:p','VRT:p']}
  rows.append(row)
 # Replay is only qualified as a surrogate if both voltage and incremental noise match.
 new=json.loads((H/'results/noise_validation.json').read_text());new={r['case']:r for r in new['cases']}
 old=json.loads((H.parent/'noise_v10/results/noise_validation.json').read_text());old={r['case']:r for r in old['cases']}
 replay=new['noise_restorer_replay_coarse'];oldcase=next(v for k,v in old.items() if 'outfirst2' in k and 'all' in k and k.endswith('coarse'))
 actual=oldcase['noise_by_subblock']['XRT.XL']['jitter_fs']
 replay_note=dict(full_chain_XL_jitter_fs=actual,ideal_voltage_replay_jitter_fs=replay['numeric_jitter_fs'],relative_difference=replay['numeric_jitter_fs']/actual-1,qualified_noise_surrogate=False,reason='Even matching deterministic output does not preserve source impedance and noise feedback; do not use this replay to infer full-chain incremental noise. Synthetic slew sweeps only compare within their own ideal-source fixture.')
 result=dict(conditions='TT27,1.2V,physical /4 divider + CML retimer/output, ideal measured-shape RF3.936GHz,10fF. Exact last3 output periods. MOS VDSAT is model operating-point quantity, not a sharp physical boundary.',cases=rows,replay=replay_note)
 (H/'results/probe_analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print(json.dumps(dict(cases=[dict(case=r['case'],voltage=r['voltage'],latches={k:dict(tail=v['MT'],steering=v['sample_current_fraction'],overlap=v['fraction_time_sample_and_hold_both_above_10_percent']) for k,v in r['latches'].items() if k in ['XD.XS2_1','XRT.XM','XRT.XS']}) for r in rows],replay=replay_note),indent=2))
if __name__=='__main__':run()
