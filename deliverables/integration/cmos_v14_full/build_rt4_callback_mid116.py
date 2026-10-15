"""One paired physical-DAC midpoint experiment; all115 circuitry/timing frozen."""
from pathlib import Path
import datetime, hashlib, json, re

ROOT=Path(__file__).resolve().parents[4]
H=ROOT/'share/deliverables/integration/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old=H/'tb/rt4_callback_margin115_tt.scs'
    oldp=H/'results/rt4_callback_margin115_protocol.json'
    review=H/'results/rt4_callback_margin115_review116.json'
    proof=json.loads(review.read_text())
    assert proof['terminal']['exit_code']==0 and proof['terminal']['stable_interval_s']>=60
    assert proof['physical_snapshot_count']==5254 and proof['counter_matches_gated_edges']
    p=json.loads(oldp.read_text())
    assert sha(oldp)==proof['protocol_sha256']
    assert all(sha(ROOT/n)==v for n,v in p['physical_inputs_sha256'].items())
    case='rt4_callback_mid116_tt';run='rt4cbmid116ssd01'
    tb=H/'tb'/(case+'.scs');pp=H/'results/rt4_callback_mid116_protocol.json'
    assert not tb.exists() and not pp.exists()
    before=old.read_text();s=before.replace('coarse8/DAC49','coarse8/DAC32')
    changes=[]
    for i in range(6):
        replacement=f'VD{i} (d{i} 0) vsource dc={1.2 if (32>>i)&1 else 0}'
        pattern=rf'^VD{i} \(d{i} 0\) vsource dc=[^\n]+'
        original=re.search(pattern,s,re.M)[0]
        s,n=re.subn(pattern,replacement,s,flags=re.M);assert n==1
        if original!=replacement:changes.append(dict(before=original,after=replacement))
    # Normalize only the header and six independent DAC source assignments.
    normalize=lambda x:re.sub(r'^VD[0-5] .*$', '',x,flags=re.M).split('\n',1)[1]
    assert normalize(s)==normalize(before) and len(changes)==2
    tb.write_text(s)
    p.update(time=datetime.datetime.now().astimezone().isoformat(),
        cases=[dict(run=run,case=case,kind='diagnostic',stop_s=7e-6,strobe_s=1e-11,expected_points=700001,requested_threads=2)],
        purpose='Measure the actual new-counter sign at fresh-verification starting midpoint DAC32, paired with completed115 DAC49/+6 counts. Determine whether these two physical-DAC points bracket target5248 under matched local conditions, without another coarse-code sweep.',
        selection_basis='DAC32 is the unchanged controller fresh-search midpoint, not a fitted next code inferred from49 without its search bounds.115 measured5254 edges/counts with actual control about.899V and evolving free bias. Only DAC source bits0/4 change; all circuit loading, initial conditions, gate timing and7us record remain identical.',
        dac=32,ideal_unloaded_dac_V=1.2*32/64,
        initialization=p['initialization'].replace('DAC49','DAC32'),
        physical_inputs_sha256={n:(sha(tb) if n.endswith('/rt4_callback_margin115_tt.scs') else v) for n,v in p['physical_inputs_sha256'].items()},
        prior115_protocol_sha256=sha(oldp),prior115_review_sha256=sha(review),
        prior115_input_sha256=sha(old),paired_changes=changes,
        paired_boundary='Independent matched local runs at fixed coarse8, DAC49 versus32. Not sequential autonomous bisection: analog state is reinitialized identically, bias still evolves, and the complete FLL FSM is absent. No two-consecutive-window or lock claim.',
        next_decision='After terminal review compare measured sign, actual control/preset, drift and counter-to-edge agreement. A bracket would support local fine authority only; do not mechanically add DAC points or repeat120us capture.')
    p['physical_inputs_sha256'].pop(old.relative_to(ROOT).as_posix())
    p['physical_inputs_sha256'][tb.relative_to(ROOT).as_posix()]=sha(tb)
    pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(protocol=pp.relative_to(ROOT).as_posix(),sha256=sha(pp),changed_sources=changes)))

if __name__=='__main__':main()
