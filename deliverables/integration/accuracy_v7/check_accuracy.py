"""Evaluate previously specified continued-window accuracy and observer effects."""
import json,re
import numpy as np
from analyze import H,R,cross

def normalized(p):
 s=p.read_text();s=re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)
 s=re.sub(r'readic="[^"]+"','readic="SAME_IC"',s)
 return s.replace('maxstep=500f','maxstep=1p')

def continuation(rows):
 protocol=json.loads((H/'results/protocol.json').read_text());by={x['case']:x for x in rows}
 out=dict(protocol=protocol['continuation'],status='pending',pass_precision=False,scope='Same physical1ps4us initial state,4us continuation at1ps vs0.5ps. Not two independent cold starts, no jitter/PVT/fullPLL signoff.')
 if not all(k in by for k in ['continue_1ps','continue_halfps']):return out
 a,b=by['continue_1ps'],by['continue_halfps'];out['status']='completed'
 if not a['sim_ok'] or not b['sim_ok']:return out
 ja=R/a['run']/a['case'];jb=R/b['run']/b['case']
 assert normalized(ja/'inputs/continue_1ps.scs')==normalized(jb/'inputs/continue_halfps.scs')
 ra=json.loads((ja/'result.json').read_text());rb=json.loads((jb/'result.json').read_text())
 assert {k:v for k,v in ra['inputs_sha256'].items() if k!='continue_1ps.scs'}=={k:v for k,v in rb['inputs_sha256'].items() if k!='continue_halfps.scs'}
 aa=np.load(H/'results'/f'{a["run"]}_{a["case"]}_samples.npz');bb=np.load(H/'results'/f'{b["run"]}_{b["case"]}_samples.npz')
 ma=aa['time']>3e-6;mb=bb['time']>3e-6
 dp=float(np.angle(np.exp(1j*(bb['obsphase'][-1]-aa['obsphase'][-1]))));dv=float(np.mean(bb['obsctrl'][mb])-np.mean(aa['obsctrl'][ma]));df=(b['transient']['mean_output_mhz']-a['transient']['mean_output_mhz'])*1e6
 lim=protocol['continuation']['precision_limits']
 out.update(cases={x['case']:x['transient'] for x in [a,b]},only_timestep_changed=True,end_phase_delta_rad=dp,mean_control_delta_v=dv,mean_output_delta_hz=df)
 out['pass_precision']=bool(a['transient']['pass_stationary'] and b['transient']['pass_stationary'] and abs(dp)<lim['max_end_phase_delta_rad'] and abs(dv)<lim['max_mean_control_delta_v'] and abs(df)<lim['max_mean_output_delta_hz'])
 return out

def dense(job):
 with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 t=d['time'];vco=cross(t,d['vp']-d['vn']);ref=cross(t,d['refb'],.6)
 out=cross(t,d['out'],.6) if 'out' in d else None
 i=np.searchsorted(vco,ref)-1;good=(i>0)&(i+1<len(vco));ref=ref[good];i=i[good]
 prev=2*np.pi*(ref-vco[i])/(vco[i]-vco[i-1]);around=2*np.pi*(ref-vco[i])/(vco[i+1]-vco[i]);ctrl=np.interp(ref,t,d['ctrl'])
 record=dict(case=job.name,ref_edges=len(ref),vco_edges=len(vco),output_edges=len(out) if out is not None else None,ref_times_s=ref.tolist(),phase_previous_period_rad=prev.tolist(),phase_surrounding_period_rad=around.tolist(),ctrl_at_ref_v=ctrl.tolist(),max_phase_definition_delta_rad=float(max(abs(np.angle(np.exp(1j*(around-prev)))))))
 record['saved_signal_scope']='VCO/reference phase and control are saved; divider out was omitted from the inherited save list, so no independent output-edge count is inferred.' if out is None else 'VCO/reference/output waveforms saved.'
 if 'obsphase' in d:
  op=np.interp(ref+500e-15,t,d['obsphase']);ov=np.interp(ref+500e-15,t,d['obsctrl'])
  record['observer_vs_dense_phase_max_rad']=float(max(abs(np.angle(np.exp(1j*(op-prev))))))
  record['observer_vs_dense_ctrl_max_v']=float(max(abs(ov-ctrl)))
 record['time_step_stats_s']={k:float(v) for k,v in zip(['minimum','median','maximum'],[np.min(np.diff(t)),np.median(np.diff(t)),np.max(np.diff(t))])}
 # No physical state was removed, except separate measurement nodes in the plain TB.
 ic=next((job/'inputs').glob('*.ic'));states={}
 for line in ic.read_text().splitlines():
  w=line.split()
  if len(w)>1 and not w[0].startswith('#'):
   try:states[w[0]]=float(w[1])
   except ValueError:continue
 delta={k:abs(float(d[k][0])-v) for k,v in states.items() if k in d}
 record['initial_readic_max_error']=max(delta.values());assert max(delta.values())<1e-10
 return record

def main():
 rows=json.loads((H/'results/validation.json').read_text());c=continuation(rows)
 (H/'results/continuation_accuracy.json').write_text(json.dumps(c,indent=2)+'\n')
 ms=[]
 for rp in sorted(R.glob('mesh*/*/result.json')):
  rec=json.loads(rp.read_text())
  if rec.get('ok') and rec.get('remote_inputs_match'):ms.append(dense(rp.parent))
 by={x['case']:x for x in ms};pairs={}
 for tag in ['1ps','halfps']:
  if not all(f'mesh_{tag}_{x}' in by for x in ['obs','plain']):continue
  a,b=by[f'mesh_{tag}_obs'],by[f'mesh_{tag}_plain'];assert a['ref_edges']==b['ref_edges']
  dphase=np.angle(np.exp(1j*(np.array(b['phase_previous_period_rad'])-a['phase_previous_period_rad'])))
  dc=np.array(b['ctrl_at_ref_v'])-a['ctrl_at_ref_v']
  pairs[tag]=dict(max_abs_phase_delta_rad=float(max(abs(dphase))),last_phase_delta_rad=float(dphase[-1]),max_abs_ctrl_delta_v=float(max(abs(dc))),last_ctrl_delta_v=float(dc[-1]))
 triplet={}
 tags=['mesh_1ps_plain','mesh_halfps_plain','mesh_quarterps_plain']
 if all(k in by for k in tags):
  aa=[by[k] for k in tags];n=min(x['ref_edges'] for x in aa)
  phase=[np.array(x['phase_previous_period_rad'][:n]) for x in aa]
  delta10=np.angle(np.exp(1j*(phase[1]-phase[0])));delta05=np.angle(np.exp(1j*(phase[2]-phase[1])))
  triplet=dict(cases=tags,common_reference_edges=n,phase_half_minus_1ps_rad=delta10.tolist(),phase_quarter_minus_half_rad=delta05.tolist(),successive_phase_delta_ratio=(delta10/delta05).tolist(),scope='Same physical initial state and full circuit. First3 reference crossings only. Near4 ratio is consistent with second-order integration error, but dynamic control response and adaptive mesh are included; not extrapolated signoff.')
 settings_pair={}
 if 'mesh_1ps_allopts' in by:
  a,b=by['mesh_1ps_plain'],by['mesh_1ps_allopts'];n=min(a['ref_edges'],b['ref_edges'])
  dp=np.angle(np.exp(1j*(np.array(b['phase_previous_period_rad'][:n])-a['phase_previous_period_rad'][:n])))
  dc=np.array(b['ctrl_at_ref_v'][:n])-a['ctrl_at_ref_v'][:n]
  settings_pair=dict(common_reference_edges=n,max_abs_phase_delta_rad=float(max(abs(dp))),max_abs_control_delta_v=float(max(abs(dc))),phase_delta_rad=dp.tolist(),control_delta_v=dc.tolist(),scope='All-options command override versus selected overrides. Same circuit/state and maxstep; first100ns only, not stationary/noise signoff.')
 out=dict(scope='250ns at1ps/0.5ps and100ns at0.25ps from same physical state; observer input draws no current, but event constraints may change numerical mesh. Dense edge analysis is independent of observer outputs. These short diagnostics are not stationary/noise signoff.',cases=ms,observer_pairs=pairs,timestep_triplet=triplet,all_options_comparison=settings_pair)
 (H/'results/mesh_validation.json').write_text(json.dumps(out,indent=2)+'\n')
 print('Continuation',c['status'],c['pass_precision'],'mesh cases',len(ms));print(json.dumps(pairs,indent=2))

if __name__=='__main__':main()
