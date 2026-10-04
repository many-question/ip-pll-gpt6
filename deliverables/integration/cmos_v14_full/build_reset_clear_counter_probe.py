"""Compare the complete 14-bit counters across carries, wrap, gate hold and reset."""
from pathlib import Path
import datetime,hashlib,json
from build_reset_clear_probe import extract
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks';DEST=B/'cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/reset_clear_quiet_validation.json';v=json.loads(proof.read_text());assert v['complete'] and v['passed']
    dynamic=H/'results/reset_clear_unit_validation.json';d=json.loads(dynamic.read_text());assert d['complete']
    assert all(x['checks']['original_guarded_function'] and x['checks']['candidate_guarded_function'] for x in d['cases'])
    dc=B/'transistor_v2/digital_cells_v2.scs';fll=B/'transistor_v2/fll_circuit.scs';cells=DEST/'reset_clear_cells_v14.scs'
    tff=extract(dc,'tx_tff').replace('tx_tff','tff_reset_clear_v14').replace('tx_dff_r0','dff_reset_clear_v14')
    counter=extract(fll,'tx_fll_counter').replace('tx_fll_counter','fll_counter_reset_clear_v14').replace('tx_tff','tff_reset_clear_v14')
    assert counter.count(') tff_reset_clear_v14')==14
    body='simulator lang=spectre\ninclude "reset_clear_cells_v14.scs"\n'+tff+'\n'+counter
    dst=DEST/'fll_counter_reset_clear_v14.scs';assert not dst.exists();dst.write_text(body,encoding='utf-8',newline='\n')
    T=1/984e6;counts=sorted({1,*[2**k-1 for k in range(1,15)],*[2**k for k in range(1,15)],16389})
    gate=[(0,0)];checks=[];cycle=20.8;old=0
    for count in counts:
        on=cycle*T;off=(cycle+count-old)*T
        gate += [(on,0),(on+1e-11,1.2),(off,1.2),(off+1e-11,0)]
        checks.append(dict(time_s=off+8*T,expected=count%(2**14),absolute_count=count,gate_off_s=off))
        cycle += count-old+12;old=count
    reset_time=(cycle+2)*T;stop=(cycle+20)*T
    checks.append(dict(time_s=reset_time+10*T,expected=0,absolute_count=None,reset_check=True))
    pwl=lambda pairs:' '.join(f'{t:.17g} {v:.17g}' for t,v in pairs)
    rows=[]
    for corner,temp in [('tt',27),('ss',60),('ff',0)]:
        case=f'reset_clear_counter_{corner}';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        nodes=lambda prefix:' '.join(prefix+str(i) for i in range(14))
        stack=[f'X{variant}.XF{i}.XF.X{stage}.XN.x' for variant in ['O','N'] for i in range(14) for stage in ['M','S']]
        s=f'''simulator lang=spectre
global 0
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section={corner}
simulator lang=spectre insensitive=no
include "cells.scs"
include "digital_cells_v2.scs"
include "fll_circuit.scs"
include "fll_counter_reset_clear_v14.scs"
simulatorOptions options temp={temp} reltol=1e-4 vabstol=1e-6 iabstol=1e-12
VDD (vdd 0) vsource dc=1.2
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period={T:.17g} width={T/2-1e-11:.17g} rise=10p fall=10p delay={.1*T:.17g}
VG (gate 0) vsource type=pwl wave=[{pwl(gate)}]
VR (reset 0) vsource type=pwl wave=[0 1.2 {10*T:.17g} 1.2 {10*T+1e-11:.17g} 0 {reset_time:.17g} 0 {reset_time+1e-11:.17g} 1.2 {stop:.17g} 1.2]
XO (clk gate reset {nodes('o')} vdd 0) tx_fll_counter
XN (clk gate reset {nodes('n')} vdd 0) fll_counter_reset_clear_v14
'''
        s+='\n'.join(f'C{variant}{i} ({variant}{i} 0) capacitor c=2f' for variant in ['o','n'] for i in range(14))+'\n'
        s+='ic '+' '.join(n+'=29.5m' for n in stack)+'\n'
        s+='save clk gate reset '+nodes('o')+' '+nodes('n')+' '+' '.join(stack)+' VDD:p\nsaveOptions options save=selected\n'
        s+=f'tran tran stop={stop:.17g} maxstep=10p method=traponly errpreset=conservative strobeperiod=2n strobeoutput=strobeonly\n'
        tb.write_text(s,encoding='utf-8',newline='\n');rows.append(dict(run='resetclearcounter01',case=case,corner=corner,temp_c=temp,tb_sha256=sha(tb)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,checks=checks,
           condition='1.2V/984MHz/2fF per bit; TT27,SS60,FF0. Gated pauses at all 14 carry boundaries and wrap, then asynchronous reset. 10ps maxstep, 2ns strobe; functional screen only.',
           clock_period_s=T,stop_s=stop,source_quiet_validation_sha256=sha(proof),source_dynamic_validation_sha256=sha(dynamic),
           dependencies_sha256={x.name:sha(x) for x in [dc,fll,cells,dst,B/'transistor_v1/cells.scs']},
           main_dut_modified=False,full_pll_acceptance=False,noise_measured=False,
           limitations=['Bus comparison is after gated-clock pauses, not an asynchronous instantaneous bus guarantee.',
                        'Two-nanosecond strobe data cannot measure clock edges, noise, jitter or average switching power.',
                        'Three paired corners at one supply and clock frequency, not complete PVT or FLL/PLL verification.',
                        'The preserved DFF running-clock test has stack kickback above1mV, although logic passed.'])
    pp=H/'results/reset_clear_counter_protocol.json';assert not pp.exists();pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(dict(cases=rows,checks=len(checks),stop_us=stop*1e6),indent=2))

if __name__=='__main__':main()
