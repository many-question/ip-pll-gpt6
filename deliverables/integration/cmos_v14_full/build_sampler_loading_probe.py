"""Prepare five physical loading/KVCO diagnostics with an external control clamp.

Actual core circuitry is unchanged. Constant VCTRL intentionally removes the
loop-filter frequency-modulation path; changing reference DC/clocking then
tests the aggregate direct reference/sampling disturbance. It does not uniquely
isolate the sampling switch from all other reference-driven loads.
"""
from pathlib import Path
import hashlib,json,re
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
cache=ROOT/'research/runs/spectre_cmos_v14_full/coretripsupply01/core_pulsetrip_supply_noise_tt/tstab_last_two_periods.npz'
with np.load(cache) as z:d={k:z[k] for k in ['time','XP.ctrl','source_sha256']}
finish=d['time'][-1];start=finish-250e-9;ix=(d['time']>start)&(d['time']<finish)
tt=np.r_[start,d['time'][ix],finish];vv=np.interp(tt,d['time'],d['XP.ctrl'])
control=float(np.trapezoid(vv,tt)/(finish-start))
source=H/'tb/core_pulsetrip_supply_noise_tt.scs';base=source.read_text()
base=re.sub(r'^(pss |pn |edge ).*\n','',base,flags=re.M)
seed=H/'state_inputs/core_pulsetrip_supply_seed_tt.ic';rows=[]
for label,reference,delta in [('clocked','clocked',0),('track','low',0),('hold','high',0),('track_vm','low',-.01),('track_vp','low',.01)]:
    case='samplerload_'+label+'_tt';voltage=control+delta;body=base
    if reference!='clocked':
        body=re.sub(r'^VR \(ref 0\).*$','VR (ref 0) vsource dc='+('1.2' if reference=='high' else '0'),body,flags=re.M)
    body+=f'\n// External diagnostic control clamp; not an accepted PLL implementation.\nVCTRL (XP.ctrl 0) vsource dc={voltage:.16g}\n'
    body+='save XP.vco_vdd XP.rx_vdd XP.rt_vdd XP.XV.XL.nfilt XP.XV.XL.tail VCTRL:p\n'
    seedname=case+'.ic';lines=[];changed=[]
    values={'XP.ctrl':voltage,'ref':1.2 if reference=='high' else 0.}
    for line in seed.read_text().splitlines():
        if not line.strip() or line.startswith('#'):lines.append(line);continue
        node=line.split()[0]
        if node in values:lines.append(f'{node} {values.pop(node):.16g}');changed.append(node)
        else:lines.append(line)
    for k,v in values.items():lines.append(f'{k} {v:.16g}');changed.append(k)
    state=H/'state_inputs'/seedname;assert not state.exists();state.write_text('\n'.join(lines)+'\n')
    body+=f'tran tran stop=750n outputstart=250n skipdc=yes readic="{seedname}" maxstep=1p method=traponly errpreset=conservative writefinal="__FINAL_STATE__"\n'
    tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    rows.append(dict(case=case,reference=reference,control_v=voltage,delta_control_v=delta,
        changed_seed_nodes=changed,tb_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),seed_sha256=hashlib.sha256(state.read_bytes()).hexdigest()))
out=dict(scope=__doc__,status='prepared_not_run',run='samplerload01',cases=rows,
    source_core_sha256=hashlib.sha256((B/'pll_noise_pulsetrip_core_v14.scs').read_bytes()).hexdigest(),
    source_seed_sha256=hashlib.sha256(seed.read_bytes()).hexdigest(),raw_measured_mean_source_sha256=str(d['source_sha256']),
    baseline_control_v=control,condition='TT27/1.2V/coarse23/CF10/baselineRT/continuousclockbank/10fF/Q5.750ns/1ps/traponly/reltol1e-5,last500nsdense,staticcontrolboundary.',
    gate='Only after banktripcorner01 all17cases completed and released its1thread short-job slot. No overlap with its last remote Spectre process.',
    measurements=['RFmean and separate last250ns windows from differential zero crossings.','Clockedcase referencehigh/low cycle frequency and harmonic least-squares edge-phase modulation.','Track/hold frequency difference; +/-10mV tracking KVCO derivative.'],
    interpretation='Large track/hold frequency split with clampedVCTRL supports switched-loading diagnosis; it is not final spur/noise acceptance or proof of a sole path.',
    main_dut_modified=False,full_pll_acceptance=False,random_jitter_measured=False)
(H/'results/sampler_loading_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(run=out['run'],control_v=control,cases=[x['case'] for x in rows]),indent=2))
