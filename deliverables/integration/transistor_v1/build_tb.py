"""PDK transistor module tests and cumulative mixed-level PLL replacements."""
from pathlib import Path
import math
import random
HERE=Path(__file__).resolve().parent
DELIVERY=HERE.parents[2]
VA=HERE.parents[1]/'blocks/behavioral_va'
PDK='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'

def header(corner='tt',temp=27):
    return f'''simulator lang=spectre
global 0
include "{PDK}" section={corner}
include "{PDK}" section=stat_noise
simulator lang=spectre insensitive=no
include "cells.scs"
parameters vddval=1.2
VDD (vdd 0) vsource dc=vddval
simulatorOptions options reltol=1e-5 vabstol=1e-7 iabstol=1e-13 temp={temp}
'''

def write(name,body,corner='tt',temp=27):
    p=HERE/'tb'/f'{name}.scs';p.parent.mkdir(parents=True,exist_ok=True)
    h=header(corner,temp)
    if 'XMETER (' in body:h=h.replace('VDD (vdd 0)','VDD (vdd_supply 0)')
    p.write_text(h+body,encoding='utf-8',newline='\n')

def main():
    for corner,temp in [('tt',27),('ss',60),('ff',0)]:
        suffix=f'{corner}_{temp}'
        for block,period,cload,delay,rise in [('reference','41.6666666666667n','60f','1n','100p'),('output','1.01626016260163n','10f','100p','20p')]:
            width=float(period[:-1])/2-float(rise[:-1])*1e-3
            write(f'tb_{block}_{suffix}',f'''
VI (inp 0) vsource type=pulse val0=0 val1=1.2 period={period} width={width}n rise={rise} fall={rise} delay={delay}
XB (inp out vdd 0) tx_{block}_buffer
CL (out 0) capacitor c={cload}
tran tran stop={'180n' if block=='reference' else '25n'} errpreset=conservative maxstep={'100p' if block=='reference' else '10p'}
save inp out VDD:p
saveOptions options save=selected
''',corner,temp)
        write(f'tb_retimer_{suffix}', '''
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period=250p width=123p rise=2p fall=2p delay=20p
VD (data 0) vsource type=pulse val0=0 val1=1.2 period=1n width=490p rise=10p fall=10p delay=70p
VE (en 0) vsource dc=1.2
XR (data clk en out vdd 0) tx_output_retimer
CL (out 0) capacitor c=5f
tran tran stop=25n errpreset=conservative maxstep=5p
save clk data out VDD:p
saveOptions options save=selected
''',corner,temp)
    write('tb_sampler_tt_27','''
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8n rise=20p fall=20p delay=1n
VP (vp 0) vsource type=sine dc=.6 ampl=.2 freq=3.936G sinephase=0
VN (vn 0) vsource type=sine dc=.6 ampl=.2 freq=3.936G sinephase=180
XS (ref vp vn hp hn vdd 0) tx_sampler
tran tran stop=130n errpreset=conservative maxstep=5p
save ref vp vn hp hn VDD:p
saveOptions options save=selected
''')
    for corner,temp in [('tt',27),('ss',60),('ff',0)]:
        src=(HERE/'tb'/f'tb_retimer_{corner}_{temp}.scs').read_text(encoding='utf-8')
        src=src[src.index('VC ('):].replace('tx_output_retimer','tx_retimer_c2mos').replace('save clk data out','save XR.q XR.qb XR.clkb clk data out')
        write(f'tb_c2mos_{corner}_{temp}',src,corner,temp)
        write(f'tb_tspc_{corner}_{temp}',src.replace('tx_retimer_c2mos','tx_retimer_tspc').replace('XR.q XR.qb XR.clkb','XR.qb XR.ck XR.XFF.b XR.XFF.a'),corner,temp)
        write(f'tb_div2_{corner}_{temp}','''
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period=250p width=123p rise=2p fall=2p delay=20p
XD (q clk q vdd 0) pll_tspc_inv
CL (q 0) capacitor c=2f
ic q=0
tran tran stop=25n errpreset=conservative maxstep=5p
save clk q VDD:p
saveOptions options save=selected
''',corner,temp)
    write('tb_filter_tt_27','''
VE (en 0) vsource type=pulse val0=0 val1=1.2 delay=1u rise=20p fall=20p width=2u period=4u
VP (pre 0) vsource dc=.6
XF (ctrl vc1 en pre vdd 0) tx_loop_filter
IIN (0 ctrl) isource type=pulse val0=0 val1=1u delay=1.2u rise=10p fall=10p width=100n period=1u
ic ctrl=0 vc1=0
tran tran stop=1.6u errpreset=conservative maxstep=1n
save en ctrl vc1 VDD:p VP:p
saveOptions options save=selected
''')
    sweep='''
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period=250p width=123p rise=2p fall=2p delay=20p
VD (data 0) vsource type=pulse val0=0 val1=1.2 period=1n width=490p rise=10p fall=10p delay=70p
VE (en 0) vsource dc=1.2
'''
    for i,sp in enumerate([.6,1.,1.5,2.,2.5]):
        sweep+=f'XR{i} (data clk en rt{i} vdd 0) tx_retimer_c2mos sp={sp}u\nCR{i} (rt{i} 0) capacitor c=5f\n'
    for i,fp in enumerate([3.,3.5,4.,4.5,5.]):
        sweep+=f'XO{i} (data out{i} vdd 0) tx_output_buffer fp={fp}u\nCO{i} (out{i} 0) capacitor c=10f\n'
    sweep+='tran tran stop=20n errpreset=conservative maxstep=5p\nsave rt0 rt1 rt2 rt3 rt4 out0 out1 out2 out3 out4\nsaveOptions options save=selected\n'
    write('tb_balance_sweep',sweep)
    for resistance in [3,5,8]:
        write(f'tb_lccore_r{resistance}','''
include "lc_core_experiment.scs"
XL (vp vn vdd 0) tx_lc_core_experiment tank_r='''+str(resistance)+'''
ic vp=1.20001 vn=1.2
tran tran stop=200n errpreset=conservative maxstep=5p
save vp vn XL.tail XL.nb VDD:p
saveOptions options save=selected
''')
    cp='include "cp_experiment.scs"\nVE (en 0) vsource dc=1.2\nVPULSE (pulse 0) vsource dc=1.2\n'
    for i,delta in enumerate([-.05,-.01,0.,.01,.05]):
        cp+=f'''VP{i} (hp{i} 0) vsource dc={.6+delta/2}
VN{i} (hn{i} 0) vsource dc={.6-delta/2}
XC{i} (hp{i} hn{i} pulse en out{i} vdd 0) tx_cp_experiment
VO{i} (out{i} 0) vsource type=pwl wave=[0 .2 10n .2 90n 1.0 100n 1.0]
'''
    cp+='tran tran stop=100n errpreset=conservative maxstep=100p\nsave VO0:p VO1:p VO2:p VO3:p VO4:p out0 VDD:p\nsaveOptions options save=selected\n'
    write('tb_cp_compliance',cp)
    cp_pulse=cp.replace('VPULSE (pulse 0) vsource dc=1.2','VPULSE (pulse 0) vsource type=pulse val0=0 val1=1.2 delay=5n period=41.6666666666667n width=2.063333333333n rise=20p fall=20p')
    cp_pulse=cp_pulse.replace('type=pwl wave=[0 .2 10n .2 90n 1.0 100n 1.0]','dc=.6').replace('stop=100n','stop=140n').replace('maxstep=100p','maxstep=20p')
    write('tb_cp_pulsed',cp_pulse)
    ss='''
VP (vp 0) vsource type=sine dc=.6 ampl=.2 freq=3.936G
VN (vn 0) vsource type=sine dc=.6 ampl=.2 freq=3.936G sinephase=180
'''
    for i in range(12):
        ss+=f'''VR{i} (ref{i} 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay={1e-9+i/12/3.936e9:.16g}
XR{i} (ref{i} refb{i} vdd 0) tx_reference_buffer
CR{i} (refb{i} 0) capacitor c=60f
XS{i} (refb{i} vp vn hp{i} hn{i} vdd 0) tx_sampler
'''
    ss+='tran tran stop=60n errpreset=conservative maxstep=5p\nsave '+' '.join(f'hp{i} hn{i}' for i in range(12))+'\nsaveOptions options save=selected\n'
    write('tb_sampler_phase',ss)
    for corner,temp in [('tt',27),('ss',60),('ff',0)]:
        write(f'tb_cml_div2_{corner}_{temp}','''
include "cml_prescaler_experiment.scs"
VP (cp 0) vsource type=sine dc=1.2 ampl=.2 freq=4G
VN (cn 0) vsource type=sine dc=1.2 ampl=.2 freq=4G sinephase=180
XD (cp cn qp qn vdd 0) tx_cml_div2
CLP (qp 0) capacitor c=5f
CLN (qn 0) capacitor c=5f
ic qp=1.1 qn=1.09
tran tran stop=100n errpreset=conservative maxstep=5p
save cp cn qp qn VDD:p
saveOptions options save=selected
''',corner,temp)
    rng=random.Random(180)
    times=[0,2.07e-9];vals=[0,0];ts=2.07e-9;state=0
    for _ in range(48):
        ts+=rng.randint(2,7)*250e-12
        times.extend([ts,ts+10e-12]);vals.extend([state,1.2-state]);state=1.2-state
    wave=' '.join(f'{t:.15g} {v}' for t,v in zip(times,vals))
    for corner,temp in [('tt',27),('ss',60),('ff',0)]:
        write(f'tb_c2mos_pattern_{corner}_{temp}',f'''
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period=250p width=105p rise=20p fall=20p delay=20p
VD (data 0) vsource type=pwl wave=[{wave}]
VE (en 0) vsource type=pulse val0=0 val1=1.2 delay=1n rise=20p fall=20p width=100n period=200n
XR (data clk en out vdd 0) tx_retimer_c2mos
CL (out 0) capacitor c=5f
tran tran stop={ts+2e-9:.15g} errpreset=conservative maxstep=5p
save clk data out VDD:p
saveOptions options save=selected
''',corner,temp)
    includes=''.join(f'ahdl_include "{p.name}"\n' for p in sorted(VA.glob('*.va')))+'ahdl_include "sampler_interface.va"\n'
    original=(HERE.parent/'va_v1/tb/top_k41.scs').read_text(encoding='utf-8')
    original=original[original.index('VREF ('):]
    includes+='ahdl_include "supply_meter.va"\n'
    for stage in range(1,7):
        body=original.replace('XREF (ref refb vdd 0) reference_buffer','XREF (ref refb vdd 0) tx_reference_buffer\nCREFLOAD (refb 0) capacitor c=60f')
        if stage>=2:body=body.replace('XOUT (retimed out vdd 0) output_buffer','XOUT (retimed out vdd 0) tx_output_buffer')
        if stage>=3:body=body.replace('XLF (ctrl vc1 enable preset 0) loop_filter','XLF (ctrl vc1 enable preset vdd 0) tx_loop_filter')
        if stage>=4:body=body.replace('XBIAS (vdd 0 vmid) bias_control','XBIAS (vdd 0 vmid) tx_bias_mid')
        if stage>=5:
            body=body.replace('XPD (refb vp vn sample pulse vdd 0) subsampling_detector','XPD (refb vp vn hp hn vdd 0) tx_sampler\nXSS (refb hp hn sample fll_sample pulse vdd 0) sampler_interface')
            body=body.replace('target sample vmid code','target fll_sample vmid code')
        if stage>=6:
            body=body.replace('XRT (div vcoclk enable retimed violations vdd 0) output_retimer','XRT (div vcoclk enable retimed vdd 0) tx_retimer_c2mos').replace(' violations','')
        body='XMETER (vdd_supply vdd 0 power_mw) supply_meter start=20u\n'+body
        body=body.replace('save ctrl vc1', 'save power_mw preset vmid hp hn fll_sample ctrl vc1') if stage>=5 else body.replace('save ctrl vc1','save power_mw preset vmid ctrl vc1')
        # Full FLL startup remains the baseline. Short tests use known code only
        # to isolate each replacement's main-loop integration before startup runs.
        write(f'top_s{stage}_k41',includes+body)
        ctrl=.6+(3.936e9-4e9/math.sqrt(1+6/255*((4/2.64)**2-1)))/20e6
        fll_line='XFLL (refb vcoclk target '+('fll_sample' if stage>=5 else 'sample')+' vmid code preset enable status locked measured vdd 0) auxiliary_fll'
        fixed=body.replace(fll_line,f'''VCODE (code 0) vsource dc=6
VEN (enable 0) vsource dc=1.2
VPRE (preset 0) vsource dc={ctrl:.16g}
// Fixed-code isolation test: no claim of acquisition or qualified FLL lock.
ic ctrl={ctrl:.16g} vc1={ctrl:.16g}''').replace('start=20u','start=4u').replace('stop=25u','stop=6u').replace('code enable status locked measured sample','code enable sample')
        write(f'loop_s{stage}_k41',includes+fixed)
        for prefix,data in [('loop',fixed),('top',body)]:
            if stage>=5:write(f'{prefix}_s{stage}_k41_moderate',includes+data.replace('errpreset=conservative','errpreset=moderate'))
        if stage>=5:
            probe=fixed.replace('stop=6u','stop=500n').replace('start=4u','start=300n')
            for mode in ['moderate','conservative']:
                write(f'probe_s{stage}_{mode}',includes+probe.replace('errpreset=conservative',f'errpreset={mode}'))
    # Moderate runs use an explicit tolerance; preserve conservative variants.
    for path in (HERE/'tb').glob('*_moderate.scs'):
        if path.name.startswith(('loop_','top_','probe_')):
            path.write_text(path.read_text(encoding='utf-8').replace('reltol=1e-5','reltol=1e-4'),encoding='utf-8',newline='\n')
    print('Generated',len(list((HERE/'tb').glob('*.scs'))),'testbenches')

if __name__=='__main__':main()
