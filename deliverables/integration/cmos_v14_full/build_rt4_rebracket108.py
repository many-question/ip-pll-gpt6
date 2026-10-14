"""Fresh-count bounded bisection after SAR; no forced coarse code or longer budget."""
from pathlib import Path
import datetime,hashlib,json
from build_capture_repair import map_module
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAME='fll_rebracket108_v14'

def main():
    pp=H/'results/rt4_rebracket108_protocol.json';assert not pp.exists()
    source=B/'fll_recheckstep_v14.v';s=source.read_text().replace('fll_recheckstep_v14',NAME)
    assert not (B/(NAME+'.v')).exists()
    start=s.index(' // Bounded correction:');end=s.index(' assign state_out=state;',start)
    s=s[:start]+''' // Discard stale SAR minima. New measurements narrow inclusive DAC bounds.
 reg [5:0] verify_low, verify_high;
 wire [6:0] lower_sum = {1'b0,verify_low}+{1'b0,dac}-7'd1;
 wire [6:0] upper_sum = {1'b0,dac}+7'd1+{1'b0,verify_high};
'''+s[end:]
    s=s.replace('checks<=0;\n   end else begin',"checks<=0; verify_low<=11; verify_high<=53;\n   end else begin")
    start=s.index('               if(measured>target) begin');end=s.index('\n             end\n           end\n         end else begin',start)
    s=s[:start]+'''               if(measured>target) begin
                 if(dac<=verify_low) begin range_error<=1; enable<=0; state<=DONE; end
                 else begin verify_high<=dac-1'b1; dac<=lower_sum[6:1]; end
               end else begin
                 if(dac>=verify_high) begin range_error<=1; enable<=0; state<=DONE; end
                 else begin verify_low<=dac+1'b1; dac<=upper_sum[6:1]; end
               end'''+s[end:]
    old='''             dac<=selected_dac;
             if(selected_dac<11 || selected_dac>53) begin range_error<=1; state<=HANDOFF; end
             else begin verify_mode<=1; good_once<=0; checks<=0; state<=SETTLE; end'''
    assert old in s
    s=s.replace(old,'''             // Midpoint is a search trial, never an accepted fixed code.
             // Always remeasure the full legal interval, even if old SAR saturated.
             dac<=32; verify_low<=11; verify_high<=53;
             verify_mode<=1; good_once<=0; checks<=0; state<=SETTLE;''')
    s=s.replace('// Candidate104: bounded variable correction; no forced code.','// Candidate108: fresh-count DAC interval bisection; original coarse SAR retained.')
    for text in [' reg [13:0] best_error;\n',' reg [5:0] best_dac;\n',
      ' wire better = (trial_error<best_error) || ((trial_error==best_error) && (dac<best_dac));\n',
      ' wire [5:0] selected_dac = better ? dac : best_dac;\n',
      " best_error<=14'h3fff;best_dac<=32;",'           if(better) begin best_error<=trial_error;best_dac<=dac;end\n']:
        assert text in s;s=s.replace(text,'')
    s=s.replace('// Capture repair: coarse32/fine128 references, actual measured-best fine DAC.\n// Select a tested fine code; do not add one to an already rejected last bit.','// Coarse32/fine128 SAR precedes fresh verification with legal DAC bounds.\n// Handoff uses two new matching measurements, never a stale minimum.')
    (B/(NAME+'.v')).write_text(s)
    mapped=map_module(NAME)
    control='pll_control_rebracket108_v14';top='pll_capture_rt4_r48_rebracket108_v14'
    cp=B/(control+'.scs');tp=B/(top+'.scs');tb=H/'tb/rt4r48_rebracket108_k41_tt.scs'
    assert not any(x.exists() for x in [cp,tp,tb])
    cp.write_text((B/'pll_control_recheckstep_v14.scs').read_text().replace('pll_control_recheckstep_v14',control).replace('fll_recheckstep_v14',NAME))
    tp.write_text((B/'pll_capture_rt4_r48_recheckstep_v14.scs').read_text().replace('pll_capture_rt4_r48_recheckstep_v14',top).replace('pll_control_recheckstep_v14',control).replace('fll_recheckstep_v14',NAME))
    tb.write_text((H/'tb/rt4r48_recheckstep_k41_tt.scs').read_text().replace('pll_capture_rt4_r48_recheckstep_v14',top))
    p=json.loads((H/'results/rt4_recheckstep_protocol.json').read_text())
    p['cases'][0].update(case=tb.stem,run='rt4bracket108ssd01',tb_sha256=sha(tb))
    review=H/'results/rt4_freebias108_review.json'
    p.update(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,candidate_top=tp.relative_to(ROOT).as_posix(),candidate_sha256=sha(tp),mapped=mapped,
      threads=4,strobe_period_s=2e-9,expected_points=60001,
      changes=['Keep the complete coarse/fine SAR sequence; discard its stale selected-DAC minimum at verification entry.',
        'Fresh verification starts at midpoint32 of legal interval11..53. Error>1 narrows the upper bound; error<-1 narrows the lower bound; next trial is the interval midpoint.',
        'Two consecutive fresh abs(error)<=1 at the same DAC are required; contradictory/empty interval or eight-check exhaustion fails without enable.',
        'No forced coarse code, unchanged32-ref settle/128-ref measurement/8 checks/120us duration and original analog dependencies.'],
      rationale='Variable-step DAC46..26 remained high through eight checks. Real-bias local probe shows coarse19 low-control RF3932.990MHz and coarse20 conditional endpoints3922.517/3939.166MHz. There is tuning headroom under these local conditions, so test fresh bisection rather than assume code19 impossible or increase time/step gain. Analog monotonicity and bias settling remain to be verified in full MOS.',
      dispatch_gate='Mapped gate-graph tests pass, prior3us diagnostic fully recovered and audited, no owned remote jobs; one independent K41 TT120us capture only.',
      evidence_boundary='New4.8fF/bisection controller candidate, not adopted. Local fixed-code probes inform this test but are not full PLL capture. No inherited low-frequency or noise pass.',
      predecessor_review_sha256=sha(review),
      physical_inputs_sha256={x.relative_to(ROOT).as_posix():sha(x) for x in [B/(NAME+'.v'),B/(NAME+'_mapped.json'),B/(NAME+'.scs'),cp,tp,tb]})
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(mapped))
if __name__=='__main__':main()
