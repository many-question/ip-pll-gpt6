"""Prepare a phase-continuous constant-fine RT4 pair from the audited full intermediate state."""
from pathlib import Path
from decimal import Decimal, ROUND_FLOOR
import datetime, hashlib, json, re

H=Path(__file__).resolve().parent; ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source_protocol=H/'results/full_pll_precision_stage_protocol.json'
    sp=json.loads(source_protocol.read_text())
    validation=H/'results/full_pll_precision_stage_validation.json'; v=json.loads(validation.read_text())
    assert v['stage_passed'] and v['protocol_sha256']==sha(source_protocol)
    j=ROOT/'research/runs/spectre_cmos_v14_full'/sp['run']/sp['case']
    rp=j/'result.json'; r=json.loads(rp.read_text())
    assert sha(rp)==v['source_result_sha256'] and r['ok'] and r['remote_inputs_match']
    final=j/'final.ic'; assert sha(final)==v['outputs']['final.ic']['sha256']
    stage_tb=H/'tb'/(sp['case']+'.scs'); assert sha(stage_tb)==sp['tb_sha256']
    # Preserve physical circuit, reference source shape, and observations from the audited stage.
    body=stage_tb.read_text()
    assert body.count('precision_steps paramset {')==1
    body=re.sub(r'precision_steps paramset \{.*?\}\n','',body,flags=re.S)
    body=body.replace('reltol=1e-4 vabstol=1e-6','reltol=1e-6 vabstol=1e-9')
    period=Decimal('41.6666666666667e-9');delay=Decimal('1e-9');offset=Decimal('15.9e-6')
    index=((offset-delay)/period).to_integral_value(rounding=ROUND_FLOOR)+1
    shifted=delay+index*period-offset
    values={s.split()[0]:float(s.split()[1]) for s in final.read_text().splitlines() if s.strip() and not s.startswith('#')}
    assert abs(values['ref'])<1e-9 and Decimal(0)<shifted<period/2
    body,count=re.subn(r'^(VR .* delay=)1n$',lambda m:m[1]+str(shifted),body,flags=re.M);assert count==1
    state=H/'state_inputs/rt4_stage15900_phase_continuous.ic';assert not state.exists();state.write_bytes(final.read_bytes())
    tran=(f'tran tran stop=2.2u maxstep=.5p strobeperiod=2n strobeoutput=strobeonly skipstop=1u method=traponly '
          f'errpreset=moderate readic="{state.name}" skipdc=yes noisefmax=160G noisefmin=1M noiseseed=11 '
          'param=isnoisy param_vec=[0 0 1u 0] writefinal="__FINAL_STATE__"')
    body,count=re.subn(r'^tran tran .*$',tran,body,flags=re.M);assert count==1
    physical={k:val for k,val in r['inputs_sha256'].items() if k.endswith('.scs') and k!=sp['case']+'.scs'}
    available={x.name:x for x in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[k])==val for k,val in physical.items())
    cases=[]
    for label,on in [('off',0),('on',1)]:
        case='full_pll_rt4_fine_'+label+'_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        tb.write_text(body.replace('param_vec=[0 0 1u 0]',f'param_vec=[0 0 1u {on}]'),encoding='utf-8',newline='\n')
        cases.append(dict(run='pllrt4fine'+label+'01',case=case,noise_enabled=bool(on),tb_sha256=sha(tb)))
    parent=H/'results/full_pll_direct_noise_pair_protocol.json';base=json.loads(parent.read_text())
    p={k:base[k] for k in ['condition','output_hz','ref_hz','stop_s','noise_start_s','measurement_start_s','edge_count',
        'band_hz','maxstep_s','reltol','vabstol','iabstol','noisefmax_hz','noisefmin_hz','seed','limitations']}
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
        parent_protocol_sha256=sha(parent),source_protocol_sha256=sha(source_protocol),source_validation_sha256=sha(validation),
        source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),source_tb_sha256=sha(stage_tb),
        source_ic_sha256=sha(final),source_elapsed_time_s=float(offset),
        text_state=state.name,text_state_sha256=sha(state),physical_dependency_hashes=physical,
        reference_phase_preservation=dict(period_s=float(period),original_delay_s=float(delay),next_source_rising_index=int(index),
            new_delay_s=float(shifted),source_ref_final_v=values['ref']),
        observations=re.search(r'^save (.*)$',body,re.M)[1].split(),physical_dut_modified=False,full_pll_acceptance=False,
        deployment_rule='Quiet first. All existing completion, numerical, initial-state, logic, and stationary-loop gates must pass before the matching noise-on is dispatched by the existing pipeline.',
        quiet_gates=dict(minimum_reference_samples=23,phase_pp_rad_max=.02,abs_phase_drift_rad_per_us_max=.01,
            maximum_rf_cycles_error=.001,maximum_out_cycles_error=.001,initial_voltage_difference_v_max=1e-9))
    p['limitations']+=['Intermediate-stage2ns samples do not establish RF stationarity. This separate dense fixed-fine quiet check must pass first.',
        'Full terminal text state copied byte-for-byte with reference phase preserved; hidden integrator history is not restored. Initialization is rechecked.',
        'The original-V14 quiet pass and running noise pair are separate evidence, not an RT4 pass.']
    dst=H/'results/full_pll_rt4_fine_pair_protocol.json';assert not dst.exists();dst.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(cases=cases,state_sha256=sha(state),reference=p['reference_phase_preservation'],physical_files=len(physical)),indent=2))

if __name__=='__main__':main()
