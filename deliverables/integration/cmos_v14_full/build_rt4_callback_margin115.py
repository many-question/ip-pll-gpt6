"""One real-DAC/free-bias/count-window diagnostic; never changes the full PLL."""
from pathlib import Path
import datetime, hashlib, json, re

ROOT = Path(__file__).resolve().parents[4]
H = ROOT/'share/deliverables/integration/cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    case='rt4_callback_margin115_tt'
    tb=H/'tb'/(case+'.scs'); pp=H/'results/rt4_callback_margin115_protocol.json'
    assert not tb.exists() and not pp.exists()
    net=ROOT/'share/deliverables/blocks/cmos_v14_full/rt4_callback110_after.scs'
    assert sha(net)=='260a50e7e62d0d25cfdfb21d6004a22f31ca38544632329448bea811dcd38f62'
    prior=H/'results/rt4_callback_k41_comparison114.json'
    assert prior.exists()
    source=H/'tb/pdkcb110_vco_after.scs'
    s=source.read_text()
    s=s.replace('VC (ctrl 0) vsource dc=.48', '\n'.join(
        [f'VD{i} (d{i} 0) vsource dc={1.2 if (49>>i)&1 else 0}' for i in range(6)]+
        ['XDAC (d0 d1 d2 d3 d4 d5 0 preset vdd 0) tx_fll_dac_pdk110_75',
         'XLF (ctrl vc1 0 preset vdd 0) tx_loop_filter_v5_pdk110_17']))
    for bit in range(8):
        s,n=re.subn(rf'VB{bit} \(b{bit} 0\) vsource dc=[^\n]+',
                    f'VB{bit} (b{bit} 0) vsource dc={1.2 if (8>>bit)&1 else 0}',s)
        assert n==1
    # Actual prehandoff CP is disabled and connected to ctrl. External gate timing
    # isolates one measurement; it does not instantiate/override the FLL FSM.
    s=re.sub(r'^VPULSE .*$', 'VPULSE (pulse 0) vsource dc=0', s, flags=re.M)
    s=re.sub(r'^VO .*\n', '',s,flags=re.M)
    s=s.replace('XCP (hp hn pulse vdd cpout vdd 0)', 'XCP (hp hn pulse 0 ctrl vdd 0)')
    cq=' '.join('cq'+str(i) for i in range(14)); m=' '.join('m'+str(i) for i in range(14))
    added='\n'.join([
        'VG (count_gate 0) vsource type=pwl wave=[0 0 1.5u 0 1.50001u 1.2 6.833333333333333u 1.2 6.833343333333333u 0]',
        'VCR (count_reset 0) vsource type=pwl wave=[0 1.2 1.458333333333333u 1.2 1.458343333333333u 0]',
        'XACQ0 (acqclk clock_mux vdd 0 vdd 0) pll_tg_pdk110_16',
        'XACQ1 (out clock_mux 0 vdd vdd 0) pll_tg_pdk110_16',
        'XACB0 (clock_mux clock_b vdd 0) pll_inv_pdk110_36',
        'XACB1 (clock_b count_clock vdd 0) pll_inv_pdk110_27',
        f'XCOUNT (count_clock count_gate count_reset {cq} vdd 0) tx_fll_counter_pdk110_71',
        f'XSN (count_gate {cq} {m} vdd 0) tx_fll_snapshot_pdk110_74'])
    s=s.replace('ic vp=',added+'\nic vp=')
    s=re.sub(r'^save .*$', 'save vp vn out acqclk count_clock XCOUNT.gclk count_gate count_reset '+m+' ctrl vc1 preset XV.XL.nb XV.XL.nfilt '+
             ' '.join('b'+str(i) for i in range(8))+' '+' '.join('d'+str(i) for i in range(6)),s,flags=re.M)
    s=s.replace('stop=4e-07 start=0 strobeperiod=5e-12','stop=7e-06 start=0 strobeperiod=1e-11')
    assert 'stop=7e-06' in s and 'vsource dc=.48' not in s
    tb.write_text('// Local fixed coarse8/DAC49 diagnostic; not autonomous FLL or PLL capture.\n'+s)
    c=dict(run='rt4cbmargin115ssd01',case=case,kind='diagnostic',stop_s=7e-6,strobe_s=1e-11,expected_points=700001,requested_threads=2)
    p=dict(time=datetime.datetime.now().astimezone().isoformat(),cases=[c],threads=2,
      mode='ax',maxstep_s=8e-12,reltol=.001,method='traponly',noise=False,
      condition='TT27/1.2V/24MHz/10fF, frozen callback110 geometry and analog parameters.',
      purpose='At the actual high-DAC recenter threshold49 and previously measured coarse8, compare physical RF/4 gated count with target5248 while free bias evolves through one128-reference-cycle measurement. No coarse-code sweep.',
      selection_basis='Prior .84V clamp is nominal ideal DAC44.8, below recenter threshold49 (ideal.91875V). Actual DAC, loop-filter preset switches and disabled CP replace the ideal control clamp. A7us local record covers1.5us settling,5.333333us counting and166.657ns drain/observation, without repeating120us acquisition.',
      coarse=8,dac=49,ideal_unloaded_dac_V=1.2*49/64,target_count=5248,target_rf_Hz=3936e6,
      count_gate_half_crossings_s=[1.500005e-6,6.833338333333333e-6],measurement_duration_s=128/24e6,
      counter_snapshot_window_s=[6.97e-6,7e-6],measurement_window_s=[1.500005e-6,6.833338333333333e-6],
      frequency_windows_s=[[1.7e-6,2e-6],[3.7e-6,4e-6],[6.5e-6,6.8e-6]],
      initialization='Real1Mohm/10pF bias, nfiltIC.728V released at t0. External fixed coarse8/DAC49; counter reset/gate externally timed. Original clock mux/buffers/counter/snapshot retained as MOS subcircuits.',
      unchanged='Frozen callback110 W/L/NF/M, derived geometry, analog component values and full-PLL RTL/netlist. This fixture adds only existing subcircuits and stimuli; no controller threshold/budget change.',
      physical_inputs_sha256={x.relative_to(ROOT).as_posix():sha(x) for x in [net,tb]},
      previous_comparison_sha256=sha(prior),source_tb_sha256=sha(source),
      completion='Two independent terminal observations>=60s,exit0/zero errors,PSF END,input/raw/log/final.ic hashes,700001 finite physical points0..7us.',
      evidence_boundary='Fixed-code local warm-bias diagnostic with externally timed gate, not autonomous SAR, coarse correction, two-window handoff, cold-start full-PLL capture, asymptotic steady state or noise. Differences from114 also include actual DAC/filter/disabledCP/counter loading, not bias-only causation.',
      resource_cap=dict(threads=18,long_jobs=4,short_jobs=1))
    pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(protocol=pp.relative_to(ROOT).as_posix(),sha256=sha(pp),input_sha256=sha(tb))))

if __name__=='__main__':main()
