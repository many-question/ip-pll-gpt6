"""Independent bounded 1..4-code correction, prompted by eight exhausted checks."""
from pathlib import Path
import datetime, hashlib, json
from build_capture_repair import map_module
H=Path(__file__).resolve().parent; ROOT=H.parents[3]; B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAME='fll_recheckstep_v14'

def main():
    pp=H/'results/rt4_recheckstep_protocol.json'; assert not pp.exists()
    source=B/'fll_recheck128_v14.v'; s=source.read_text().replace('fll_recheck128_v14',NAME)
    assert not (B/(NAME+'.v')).exists()
    s=s.replace('assign state_out=state;', '''// Bounded correction: floor(error/2), limited to1..4 codes.
 // Small errors retain a single step. No change to acceptance or check budget.
 wire [5:0] correction = (trial_error>=8) ? 6'd4 :
                         (trial_error>=6) ? 6'd3 :
                         (trial_error>=4) ? 6'd2 : 6'd1;
 assign state_out=state;''')
    assert s.count("else dac<=dac-1'b1;")==1 and s.count("else dac<=dac+1'b1;")==1
    s=s.replace("else dac<=dac-1'b1;", "else dac <= ((dac-6'd11)<correction) ? 6'd11 : dac-correction;")
    s=s.replace("else dac<=dac+1'b1;", "else dac <= ((6'd53-dac)<correction) ? 6'd53 : dac+correction;")
    (B/(NAME+'.v')).write_text('// Candidate104: bounded variable correction; no forced code.\n'+s)
    mapped=map_module(NAME)
    control='pll_control_recheckstep_v14'; top='pll_capture_rt4_r48_recheckstep_v14'
    cp=B/(control+'.scs');tp=B/(top+'.scs');tb=H/'tb/rt4r48_recheckstep_k41_tt.scs'
    assert not any(p.exists() for p in [cp,tp,tb])
    cp.write_text((B/'pll_control_recheck_v14.scs').read_text().replace('pll_control_recheck_v14',control).replace('fll_recheck128_v14',NAME))
    tp.write_text((B/'pll_capture_rt4_r48_recheck_v14.scs').read_text().replace('pll_capture_rt4_r48_recheck_v14',top).replace('pll_control_recheck_v14',control).replace('fll_recheck128_v14',NAME))
    tb.write_text((H/'tb/rt4r48_recheck_k41_tt.scs').read_text().replace('pll_capture_rt4_r48_recheck_v14',top))
    p=json.loads((H/'results/rt4_recheck_protocol.json').read_text())
    c=p['cases'][0];c.update(case=tb.stem,run='rt4stepk41ssd01',tb_sha256=sha(tb))
    p.update(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,
        candidate_top=tp.relative_to(ROOT).as_posix(),candidate_sha256=sha(tp),mapped=mapped,
        changes=['Only the verification DAC update changes: step=max(1,min(4,floor(abs(count-target)/2))). Saturate at11..53; next out-of-range correction at a rail fails.',
                 'Keep SAR,32-ref settle,128-ref measure,two consecutive abs(error)<=1,8 checks,normal handoff and120us duration.'],
        rationale='Completed predecessor: recheck errors18,15,15,13,12,11,10,8 at DAC44..37. One-code corrections exhausted8 checks without handoff. Bounded larger steps test this specific limitation; drifting-plant cause remains unresolved.',
        dispatch_gate='Mapped-graph tests pass; prior task fully collected and independently reviewed; no owned remote jobs. One new K41 TT capture only.',
        evidence_boundary='Separate4.8fF variable-step controller candidate. No inheritance of functional/noise passes from any earlier version.',
        physical_inputs_sha256={x.relative_to(ROOT).as_posix():sha(x) for x in [B/(NAME+'.v'),B/(NAME+'_mapped.json'),B/(NAME+'.scs'),cp,tp,tb]})
    pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(mapped))

if __name__=='__main__':main()
