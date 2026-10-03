"""Use measured SS tank shape for controlled original/candidate interface tests.

External Fourier replay is noiseless and zero impedance. A dense text-state
restart is not independent capture, and the waveform is frequency-normalized.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
j=ROOT/'research/runs/spectre_cmos_v14_full/ssinterfacedense01/ss_interface_dense'
rec=json.loads((j/'result.json').read_text());assert rec['ok'] and rec['remote_inputs_match']
assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
p=j/'waveforms.npz';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(p)==rec['local_outputs_sha256']['waveforms.npz']
with np.load(p) as z:d={k:z[k] for k in ['time','XP.vp','XP.vn','XP.clk','XP.q1','XP.data','out']}
t=d['time'];e=cross(t,d['XP.vp']-d['XP.vn'],0)[-65:];assert len(e)==65
phase=np.arange(1024)/1024;theta=2*np.pi*phase
A=np.column_stack([np.ones(len(phase))]+[f(n*theta) for n in range(1,21) for f in [np.cos,np.sin]])
body=['`include "disciplines.vams"','`include "constants.vams"','// External measured SS tank replay. No VCO noise or source impedance.',
 'module tank_replay_ss_v14(vp,vn,vss);','output vp,vn;input vss;electrical vp,vn,vss;','parameter real frequency=3.936G;','real theta;','analog begin','theta=2*`M_PI*frequency*$abstime;']
meta=dict(scope=__doc__,source=p.relative_to(ROOT).as_posix(),source_sha256=sha(p),source_condition='Old full complete_v14,SS60/1.2V/K41/M4/10fF,Q5,coarse24/DAC36;1ps,100ns text-final-state restart,last50ns dense. RFshape extraction, not locked-state signoff.',source_rf_mhz=float(1e-6/np.mean(np.diff(e))),cycles=64,source_window_us=[float(e[0]*1e6),float(e[-1]*1e6)],fit={})
for port in ['vp','vn']:
 wave=np.array([np.interp(a+(b-a)*phase,t,d['XP.'+port]) for a,b in zip(e[:-1],e[1:])]);avg=wave.mean(axis=0)
 coef=np.linalg.lstsq(A,avg,rcond=None)[0];fit=A@coef
 expr=f'{coef[0]:.16g}'+''.join(f'+({coef[2*n-1]:.16g})*cos({n}*theta)+({coef[2*n]:.16g})*sin({n}*theta)' for n in range(1,21))
 body.append(f'V({port},vss)<+{expr};')
 meta['fit'][port]=dict(dc_v=float(coef[0]),range_v=[float(min(avg)),float(max(avg))],rms_fit_error_v=float(np.sqrt(np.mean((fit-avg)**2))),max_fit_error_v=float(max(abs(fit-avg))),max_cycle_deviation_v=float(max(abs(wave-avg).flatten())),coefficients=coef.tolist())
body+=['end','endmodule'];(B/'tank_replay_ss_v14.va').write_text('\n'.join(body)+'\n')
cases=[]
for kind,bank in [('base','cmos_even_bank_acq_v14'),('boost','bank_preboost50_v14')]:
 for m in [4,6,10]:
  case=f'banksswave{kind}_m{m}_ss';cases.append(case)
  s=(H/'tb'/f'bankboostrf_m{m}_ss.scs').read_text().replace('bank_preboost50_v14',bank).replace('tank_replay_full_v14','tank_replay_ss_v14').replace('stop=100n outputstart=60n','stop=60n outputstart=20n')
  if kind=='base':s=s.replace('XD.ck XD.gn XD.cb','XD.ck XD.ckb')
  (H/'tb'/(case+'.scs')).write_text(s)
meta['cases']=cases
(H/'results/ss_waveform_replay.json').write_text(json.dumps(meta,indent=2)+'\n')
print(' '.join(cases));print('SS waveform frequency MHz',meta['source_rf_mhz']);print({k:{x:y for x,y in v.items() if x!='coefficients'} for k,v in meta['fit'].items()})
