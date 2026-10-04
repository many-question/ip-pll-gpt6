"""Prepare a20ns warm-transient factorial check, not another long PSS sweep.

Two integration methods at two maximum steps separate current-waveform method
and mesh sensitivity. No device, source, seed or accuracy-tolerance changes.
"""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=H/'tb/core_pulsetrip_late_noise_tt.scs';body=src.read_text()
body=re.sub(r'^(?:pss |pn |edge ).*\n','',body,flags=re.M)
seed=H/'state_inputs/core_pulsetrip_late_seed_tt.ic';rows=[]
for method in ['traponly','gear2only']:
    for step in ['1p','0.5p']:
        case='coremethod_'+('trap' if method=='traponly' else 'gear')+('_1ps_tt' if step=='1p' else '_halfps_tt')
        tb=body+f'\ntran tran stop=20n outputstart=5n skipdc=yes readic="{seed.name}" maxstep={step} method={method} errpreset=conservative writefinal="__FINAL_STATE__"\n'
        target=H/'tb'/(case+'.scs');assert not target.exists();target.write_text(tb)
        rows.append(dict(case=case,method=method,maxstep_s=1e-12 if step=='1p' else .5e-12,tb_sha256=sha(target)))
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='coremethod01',cases=rows,
    source_tb_sha256=sha(src),seed_sha256=sha(seed),seed_time_alignment='Localtime0 has the same reference and250ns forcing phase as source3us; actual saved physical state, not coldstart or native continuation.',
    evidence='results/core_current_waveform.json: rapid supply-current content in an otherwise nearly periodic voltage trajectory; full PSS first residual is often a current branch. Origin not proved.',
    condition='Same actualLC diagnostic core, TT27/1.2V/Q5/coarse23/CF10/originalRT/10fF; reltol1e-5/vabstol1e-7/iabstol1e-13.20ns warm transient, last15ns dense.',
    measurements=['Deterministic Hann-window current energy above100GHz and250GHz; interpolation and leakage controls, not noisePSD.','RF/output frequency, swing and common-time waveforms; mesh and integration-method sensitivity.'],
    launch_gate='Reuse sampler tuning one-thread short slot only after both results complete; do not overlap its finite batch. Four20ns cases bounded, no automatic long PSS.',
    limits='Short trajectories cannot validate PLL lock, fullperiod consistency, lowfrequency noise, PSS orRMS. A method difference alone does not prove which solution is accurate.',
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_method_probe_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print([x['case'] for x in rows])
