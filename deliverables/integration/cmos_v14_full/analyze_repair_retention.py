"""Analyze recovered same-DUT native precision and retention branches.

The root retention run uses the actual cold terminal voltages/currents, not a
native continuation of cold capture. Only its own subsequent native branches
preserve simulator history. Never join these to the 64 us cold trajectory.
"""
from pathlib import Path
import hashlib,json,contextlib,io
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
from analyze import loop
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=json.loads((H/'results/boundary_pll_capture_v14.json').read_text())['source_hashes']
rows=[]
for label,runs in [('strict',['repairstrict02']),('retention',['repairretain01','repairretain02'])]:
 jobs=[R/run/'repair_retain_tt' for run in runs]
 row=dict(kind=label,runs=runs,status='pending',scope=__doc__);rows.append(row)
 if not all((j/'result.json').exists() for j in jobs):continue
 records=[json.loads((j/'result.json').read_text()) for j in jobs]
 if (jobs[-1]/'cancellation.json').exists():
  row['status']='observed_restart_then_deliberately_stopped'
  row['diagnostic']='results/precision_diagnostics.json'
  row['note']='Not a completed retention test. Strict independent reset followup is repaircoldstrict01.'
  continue
 if 'spectre completes with 0 errors' not in (jobs[-1]/'spectre.out').read_text(errors='replace'):
  row['status']='incomplete_or_failed';continue
 datasets=[];sources={}
 for j,rec in zip(jobs,records):
  assert rec['remote_inputs_match'] and rec['local_outputs_sha256']
  assert all(rec['inputs_sha256'][k]==v and sha(j/'inputs'/k)==v for k,v in expected.items())
  wave=j/'waveforms.npz'
  if not wave.exists():
   # The runner intentionally marks a native-checkpoint stop incomplete. Its
   # raw prefix is usable only as the parent of the matching resumed segment.
   assert j!=jobs[-1] and list((j/'checkpoints').glob('*.json'))
   wave=j/'checkpoint_waveforms.npz'
   raw=j/'repair_retain_tt.raw'/'tran.tran.tran'
   assert raw.is_file()
   with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    data=parse_psf_ascii_directory(raw.parent)
   data={k:np.atleast_1d(v) for k,v in data.items() if k!='units' and np.asarray(v).dtype.kind in 'biufc'}
   np.savez_compressed(wave,**data)
   row.setdefault('checkpoint_prefixes',[]).append(dict(raw=raw.relative_to(ROOT).as_posix(),raw_sha256=sha(raw),waveform_sha256=sha(wave),scope='Incomplete native parent prefix; not a standalone acceptance run.'))
  else:
   assert sha(wave)==rec['local_outputs_sha256']['waveforms.npz']
  with np.load(wave) as z:datasets.append({k:z[k] for k in z.files if k!='units'})
  sources[(j/'result.json').relative_to(ROOT).as_posix()]=sha(j/'result.json')
  native=rec.get('native_state')
  if native:
   assert native['remote_hash_match'] and sha(ROOT/native['local'])==native['sha256']
 if label=='strict':
  assert records[0]['native_state']['source_snapshot']=='repairretain01'
  tb=(jobs[0]/'inputs/repair_retain_tt.scs').read_text()
  assert 'maxstep=1p' in tb and 'reltol=1e-5' in tb
  assert datasets[0]['time'][-1]-datasets[0]['time'][0]>3e-6
 else:
  assert records[1]['native_state']['source_snapshot']==runs[0]
  assert records[0]['inputs_sha256']['repair_actual64_tt.ic']==records[1]['inputs_sha256']['repair_actual64_tt.ic']
  for j in jobs:
   tb=(j/'inputs/repair_retain_tt.scs').read_text()
   assert 'maxstep=4p' in tb and 'reltol=1e-4' in tb
 keys=set.intersection(*(set(d) for d in datasets));parts=[]
 for i,d in enumerate(datasets):
  sel=d['time']<datasets[i+1]['time'][0] if i+1<len(datasets) else np.ones(len(d['time']),bool)
  parts.append({k:d[k][sel] for k in keys if len(d[k])==len(d['time'])})
 d={k:np.concatenate([p[k] for p in parts]) for k in parts[0]};t=d['time']
 assert np.all(np.diff(t)>0) and max(np.diff(t))<2.1e-9
 row.update(status='completed',sources=sources,stationarity=loop(d),
   native_state=records[-1].get('native_state'),dut_dependency_hashes_verified=True,
   time_range_us=[float(t[0]*1e6),float(t[-1]*1e6)])
 row['ever_restart']=bool(np.any(d['XP.restart']>.6))
 row['whole_window_qualified_high']=bool(np.all(d['qualified']>1))
 late=t>=t[-1]-1e-6
 row['logic_high_fraction']={k:float(np.mean(d[k][late]>.6)) for k in ['qualified','frequency_good','cfg_ready','range_error','XP.en','XP.XC.acquired']}
 row['held_state_screen_passed']=bool(row['stationarity']['passed'] and not row['ever_restart'] and
  all(row['logic_high_fraction'][k]==1 for k in ['qualified','frequency_good','cfg_ready','XP.en','XP.XC.acquired']) and row['logic_high_fraction']['range_error']==0)
 windows=[('last_1us',max(t[0],t[-1]-1e-6),t[-1])]
 if label=='retention':
  assert t[0]==0 and t[-1]>=35.999e-6
  windows.append(('full_32us_control_period',4e-6,36e-6))
 row['power_windows']={}
 for name,a,b in windows:
  assert t[0]<=a and b<=t[-1]+1e-15
  energykeys={'total':'energy_nj',**{k:'energy_'+k+'_nj' for k in ['vco','rx','rt']}}
  power={k:float((np.interp(b,t,d[v])-np.interp(a,t,d[v]))/((b-a)*1e6)) for k,v in energykeys.items()}
  power['other']=power['total']-sum(power[k] for k in ['vco','rx','rt'])
  sel=(t>=a)&(t<=b)
  row['power_windows'][name]=dict(window_us=[a*1e6,b*1e6],power_mw=power,
   qualified_all_high=bool(np.all(d['qualified'][sel]>1)),frequency_good_all_high=bool(np.all(d['frequency_good'][sel]>1)))
 row['power_boundary']='Internal-step energy endpoint differences of all PLL supply. Text seed retained XE:idt0 offset; the offset cancels. No absolute initial energy is treated as consumed DUT energy.'
 row['edge_statistics']={}
 for block in ['reference','rfclock','output']:
  row['edge_statistics'][block]={q:dict(mean=float(np.mean(d[block+'_'+q][late])),minimum=float(min(d[block+'_'+q][late])),maximum=float(max(d[block+'_'+q][late]))) for q in ['rise_ns','fall_ns','period_ns','duty_percent']}
 row['edge_boundary']='Internal-step held edge observers sampled every2ns; not random jitter or a uniformly weighted census of every RF cycle.'
 row['numerical_scope']='Native1ps/reltol1e-5 branch after terminal-state initialization has settled. Does not revalidate 64us FLL search at strict precision.' if label=='strict' else '4ps/reltol1e-4 same-DUT terminal-state retention; not uninterrupted cold-to100us capture.'
 if label=='retention':
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,constrained_layout=True)
  ax[0].plot(t*1e6,np.unwrap(d['obsphase']),lw=.7);ax[0].set_ylabel('RF phase at ref (rad)')
  ax[1].plot(t*1e6,d['qualified'],label='qualified');ax[1].plot(t*1e6,d['XP.restart'],label='restart');ax[1].set_ylabel('Logic (V)');ax[1].legend(ncol=2)
  edges=np.arange(0,36.001,1);energy=np.interp(edges*1e-6,t,d['energy_nj'])
  ax[2].stairs(np.diff(energy),edges,label='1 us energy differences');ax[2].axhline(4,color='#b91c1c',ls='--',label='4 mW limit')
  ax[2].set_ylabel('Total supply (mW)');ax[2].set_xlabel('Time from terminal-state initialization (us)');ax[2].legend(ncol=2)
  for a in ax:a.grid(alpha=.2);a.axvspan(4,36,color='#10b981',alpha=.07)
  fig.suptitle('Complete capture V14: TT 27 C, 1.2 V, 984 MHz, 10 fF, Q5 RLC\n4 ps / reltol 1e-4; 32 us control-period power = '+format(row['power_windows']['full_32us_control_period']['power_mw']['total'],'.6f')+' mW')
  fig.savefig(H/'results/figures/repair_retention.png',dpi=150);plt.close(fig)
out=dict(scope=__doc__,cases=rows)
(H/'results/repair_retention.json').write_text(json.dumps(out,indent=2)+'\n')
for row in rows:print(row['kind'],row['status'],row.get('held_state_screen_passed'))
