"""One fresh-count coarse adjustment near a fine-DAC rail; unchanged total budget."""
from pathlib import Path
import datetime,hashlib,json
from build_capture_repair import map_module
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAME='fll_recenter109_v14'

def main():
    pp=H/'results/rt4_recenter109_protocol.json';assert not pp.exists()
    source=B/'fll_rebracket108_v14.v';s=source.read_text().replace('fll_rebracket108_v14',NAME)
    assert not (B/(NAME+'.v')).exists()
    s=s.replace('reg verify_mode, good_once;','reg verify_mode, good_once, coarse_recentered;')
    s=s.replace('checks<=0; verify_low<=11;', 'checks<=0; coarse_recentered<=0; verify_low<=11;')
    s=s.replace(' assign state_out=state;', ''' // Four DAC codes of edge margin are a candidate design assumption.
 // A fresh signed count can request at most one neighboring coarse code.
 wire need_slower = (dac<=15) && (measured>target);
 wire need_faster = (dac>=49) && (measured<target);
 assign state_out=state;''')
    old='''           if(trial_error<=1 && good_once) begin state<=HANDOFF; end'''
    assert old in s
    s=s.replace(old,'''           if(need_slower || need_faster) begin
             good_once<=0;
             if(coarse_recentered || checks==7 || (need_slower && coarse==255) || (need_faster && coarse==0)) begin
               range_error<=1; enable<=0; state<=DONE;
             end else begin
               coarse<=need_slower ? coarse+1'b1 : coarse-1'b1;
               coarse_recentered<=1; checks<=checks+1'b1;
               dac<=32; verify_low<=11; verify_high<=53;
             end
           end else if(trial_error<=1 && good_once) begin state<=HANDOFF; end''')
    s=s.replace('// Candidate108: fresh-count DAC interval bisection; original coarse SAR retained.',
      '// Candidate109: original SAR then fresh fine bisection with one automatic coarse recenter.')
    (B/(NAME+'.v')).write_text(s)
    mapped=map_module(NAME)
    control='pll_control_recenter109_v14';top='pll_capture_rt4_r48_recenter109_v14'
    cp=B/(control+'.scs');tp=B/(top+'.scs');tb=H/'tb/rt4r48_recenter109_k41_tt.scs'
    assert not any(x.exists() for x in [cp,tp,tb])
    cp.write_text((B/'pll_control_rebracket108_v14.scs').read_text().replace('rebracket108','recenter109'))
    tp.write_text((B/'pll_capture_rt4_r48_rebracket108_v14.scs').read_text().replace('rebracket108','recenter109'))
    tb.write_text((H/'tb/rt4r48_rebracket108_k41_tt.scs').read_text().replace('rebracket108','recenter109'))
    p=json.loads((H/'results/rt4_rebracket108_protocol.json').read_text())
    p['cases'][0].update(case=tb.stem,run='rt4center109ssd01',tb_sha256=sha(tb))
    review=H/'results/rt4_rebracket_detail109.json'
    p.update(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,candidate_top=tp.relative_to(ROOT).as_posix(),candidate_sha256=sha(tp),mapped=mapped,
      changes=['Original coarse/fine SAR and fresh fine bisection retained.',
        'At fresh DAC<=15 with positive count error, increment coarse once; at DAC>=49 with negative error, decrement once. Direction is measured, no forced absolute coarse code.',
        'After a coarse change restart DAC32/bounds11..53, clear previous good count, and consume the same global eight-check budget. At most one coarse correction; bounds/second correction/budget failure never enables PLL.',
        'Two fresh abs(error)<=1 measurements at the same coarse/DAC are still required. No change to32-ref settle,128-ref count,8-check cap,120us duration,supervisor or analog geometry.'],
      rationale='Bisection108 reached DAC11/coarse19 and two +1 counts, enabled PLL94.588us but never qualified; RF remained high and supervisor restarted115.920us. Test measured-direction adjacent coarse selection for fine tuning headroom; phase capture and bias drift remain unisolated. Four-code edge margin is an explicit candidate assumption, not a proven PVT limit.',
      dispatch_gate='Mapped graph tests pass;108 capture fully recovered, two stable terminal audits and independent failed-capture review; no owned remote jobs; one K41 TT120us only.',
      evidence_boundary='Independent4.8fF/automatic-coarse-recenter candidate, not adopted. No inherited low-frequency or noise result. Geometry AD/AS/PD/PS still uses assumed240nm diffusion, not layout extraction.',
      predecessor_review_sha256=sha(review),
      physical_inputs_sha256={x.relative_to(ROOT).as_posix():sha(x) for x in [B/(NAME+'.v'),B/(NAME+'_mapped.json'),B/(NAME+'.scs'),cp,tp,tb]})
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(mapped))
if __name__=='__main__':main()
