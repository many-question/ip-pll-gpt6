"""Independent RT4 range48 candidate with measured, bounded fine recheck.

No fixed coarse/DAC override. Existing issued circuits and protocols stay intact.
"""
from pathlib import Path
import datetime, hashlib, json
from build_capture_repair import map_module

H=Path(__file__).resolve().parent; ROOT=H.parents[3]
B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAME='fll_recheck128_v14'

def main():
    protocol=H/'results/rt4_recheck_protocol.json'
    assert not protocol.exists() and not (B/(NAME+'.v')).exists()
    baseline=json.loads((H/'results/rt4_adopted_baseline.json').read_text())
    assert all(sha(ROOT/d['path'])==d['sha256'] for d in baseline['dependencies'])
    s=(B/'fll_best128_v14.v').read_text().replace('module fll_best128_v14','module '+NAME)
    s=s.replace('reg [5:0] best_dac;','reg [5:0] best_dac;\n reg verify_mode, good_once;\n reg [2:0] checks;')
    s=s.replace('enable<=0; range_error<=0;','enable<=0; range_error<=0; verify_mode<=0; good_once<=0; checks<=0;')
    s=s.replace('if(tick==7)', 'if(tick==(verify_mode ? 31 : 7))')
    old='''end else begin
           if(better) begin best_error<=trial_error;best_dac<=dac;end'''
    assert old in s
    s=s.replace(old,'''end else if(verify_mode) begin
           // Remeasure the currently applied code; never reuse an older minimum.
           // Two consecutive 128-ref windows within one RF count (0.75MHz).
           if(trial_error<=1 && good_once) begin state<=HANDOFF; end
           else if(checks==7) begin range_error<=1; enable<=0; state<=DONE; end
           else begin
             checks<=checks+1'b1;
             if(trial_error<=1) good_once<=1;
             else begin
               good_once<=0;
               if(measured>target) begin
                 if(dac<=11) begin range_error<=1; enable<=0; state<=DONE; end
                 else dac<=dac-1'b1;
               end else begin
                 if(dac>=53) begin range_error<=1; enable<=0; state<=DONE; end
                 else dac<=dac+1'b1;
               end
             end
           end
         end else begin
           if(better) begin best_error<=trial_error;best_dac<=dac;end''')
    old='''if(selected_dac<11 || selected_dac>53) range_error<=1;
             state<=HANDOFF;'''
    assert old in s
    s=s.replace(old,'''if(selected_dac<11 || selected_dac>53) begin range_error<=1; state<=HANDOFF; end
             else begin verify_mode<=1; good_once<=0; checks<=0; state<=SETTLE; end''')
    (B/(NAME+'.v')).write_text('// Candidate: bounded fresh-count validation before PLL handoff.\n'+s,encoding='utf8')
    mapped=map_module(NAME)
    control='pll_control_recheck_v14';top='pll_capture_rt4_r48_recheck_v14'
    p=B/(control+'.scs');assert not p.exists()
    p.write_text((B/'pll_control_capture_v14.scs').read_text().replace('pll_control_capture_v14',control).replace('fll_best128_v14',NAME),encoding='utf8')
    p=B/(top+'.scs');assert not p.exists()
    p.write_text((B/'pll_capture_rt4bank_range48_v14.scs').read_text().replace('pll_capture_rt4bank_range48_v14',top).replace('pll_control_capture_v14',control).replace('fll_best128_v14',NAME),encoding='utf8')
    tb=H/'tb/rt4r48_recheck_k41_tt.scs';assert not tb.exists()
    tb.write_text((H/'tb/rt4r48_k41_tt.scs').read_text().replace('pll_capture_rt4bank_range48_v14',top).replace('stop=64u','stop=120u'),encoding='utf8')
    oldp=json.loads((H/'results/rt4_range48_repair_protocol.json').read_text())
    case=next(c.copy() for c in oldp['cases'] if c['case']=='rt4r48_k41_tt')
    case.update(case=tb.stem,run='rt4recheckk41ssd01',stop_s=120e-6,tb_sha256=sha(tb))
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,
        candidate_top=p.relative_to(ROOT).as_posix(),candidate_sha256=sha(p),candidate_adopted=False,
        cases=[case],mode='ax',preset_override='all',maxstep_s=8e-12,reltol=1e-3,
        method='traponly',noise=False,capture_screen=oldp['capture_screen'],
        changes=['Keep coarse and fine SAR; remeasure selected DAC after32-ref settling.',
          'Correct by one DAC count according to fresh measured frequency, within11..53.',
          'Require two consecutive128-ref windows within1 count of target before normal handoff.',
          'At most8 rechecks; exhausted budget or rail -> range_error, no enable.'],
        rationale='Completed range48 K41 shows stale measured-best DAC46 and RF drift before handoff; causal source remains unresolved. Test recheck/correction directly, no forced code.',
        unchanged='4.8fF analog circuit, Q5/CF10, bias, RT4, divider, sampler, CP, filter, supervisor and original adopted4.4fF baseline.',
        mapped=mapped,condition=oldp['condition'],capture_initialization=oldp['capture_initialization'],
        dispatch_gate='Mapped-graph directed tests pass; no existing owned Spectre jobs/local range48 workers. One cold K41 capture only. No automatic replay or more cases.',
        stop_reason='120us bounds original search plus at most8 extra6.833us checks and >=10us post-handoff observation.',
        resource_cap=dict(threads=18,long_jobs=4,short_jobs=1),
        evidence_boundary='Unadopted controller/4.8fF candidate. Original three low-end passes do not transfer to modified controller. No jitter or full range acceptance.',
        physical_inputs_sha256={str(x.relative_to(ROOT)).replace('\\','/'):sha(x) for x in [B/(NAME+'.v'),B/(NAME+'_mapped.json'),B/(NAME+'.scs'),B/(control+'.scs'),p,tb]})
    protocol.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(protocol=str(protocol),mapped=mapped),ensure_ascii=False))

if __name__=='__main__':main()
