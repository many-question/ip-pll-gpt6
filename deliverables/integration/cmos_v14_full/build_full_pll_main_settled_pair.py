"""Continue the unchanged original PLL from its completed fine-precision state."""
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parent=H/'results/full_pll_main_strict_pair_protocol.json';p=json.loads(parent.read_text())
    j=ROOT/'research/runs/spectre_cmos_v14_full/pllmainstrictoff01/full_pll_main_strict_off_tt'
    r=json.loads((j/'result.json').read_text());assert r['ok'] and r['remote_inputs_match']
    v=json.loads((H/'results/full_pll_main_strict_pair_validation.json').read_text())['cases'][0]
    assert v['completed'] and v['status_stable'] and v['recovery']['numerically_clean']
    assert not v['stationarity']['passed']
    final=j/'final.ic';assert sha(final)==r['local_outputs_sha256']['final.ic']
    available={x.name:x for x in (H.parents[1]/'blocks').glob('*/*.scs')}
    assert all(sha(available[k])==digest for k,digest in p['physical_dependency_hashes'].items())
    # Reset simulation time only. Preserve the external reference's physical phase.
    # The source final state is during its low level, so the next rising edge
    # can be represented by a positive pulse delay with no waveform discontinuity.
    body=(H/'tb/full_pll_main_strict_off_tt.scs').read_text()
    period=Decimal('41.6666666666667e-9');delay=Decimal('1e-9');offset=Decimal('2.2e-6')
    index=((offset-delay)/period).to_integral_value(rounding=ROUND_FLOOR)+1
    shifted=delay+index*period-offset
    values={s.split()[0]:float(s.split()[1]) for s in final.read_text().splitlines() if s.strip() and not s.startswith('#')}
    assert abs(values.get('ref',0))<1e-9 and Decimal(0)<shifted<period/2
    state=H/'state_inputs/main_fine2200_phase_continuous.ic';assert not state.exists();state.write_bytes(final.read_bytes())
    body=body.replace('main_strict64_no_observer.ic',state.name)
    body,count=re.subn(r'^(VR .* delay=)1n$',lambda m:m[1]+str(shifted),body,flags=re.M);assert count==1
    cases=[]
    for label,on in [('off',0),('on',1)]:
        case='full_pll_main_settled_'+label+'_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        tb.write_text(body.replace('param_vec=[0 0 1u 0]',f'param_vec=[0 0 1u {on}]'),encoding='utf-8',newline='\n')
        cases.append(dict(run='pllmainsettled'+label+'01',case=case,noise_enabled=bool(on),tb_sha256=sha(tb)))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
        parent_protocol_sha256=sha(parent),source_result=(j/'result.json').relative_to(ROOT).as_posix(),
        source_result_sha256=sha(j/'result.json'),source_tb_sha256=sha(j/'inputs/full_pll_main_strict_off_tt.scs'),
        source_ic_sha256=sha(final),source_absolute_time_s=float(offset),
        source_stationarity=v['stationarity'],text_state=state.name,text_state_sha256=sha(state),
        reference_phase_preservation=dict(period_s=float(period),original_delay_s=float(delay),
            next_source_rising_index=int(index),new_delay_s=float(shifted),source_ref_final_v=values.get('ref',0)),
        physical_dut_modified=False,full_pll_acceptance=False)
    for k in ['removed_nonphysical_ic_entries','source_capture','source_capture_sha256']:p.pop(k,None)
    p['limitations']+=['Source first fine run failed the original full1us stationarity gate. Decaying short-window drift only motivates more settling; it does not override that failure.',
        'All text terminal states are copied byte-for-byte. Reference delay is translated by the source stop time. Hidden integration history is not restored; fresh initialization must be rechecked.']
    dst=H/'results/full_pll_main_settled_pair_protocol.json';assert not dst.exists();dst.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(cases=cases,state_sha256=sha(state),reference=p['reference_phase_preservation']),indent=2))

if __name__=='__main__':main()
