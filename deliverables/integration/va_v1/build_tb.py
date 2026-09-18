"""Generate standalone Spectre module and structural top testbenches."""
from pathlib import Path
import json
import sys
import math
HERE=Path(__file__).resolve().parent
BLOCKS=HERE.parents[1]/'blocks/behavioral_va'
V1=HERE.parents[1]/'architecture/behavioral_v1'
sys.path.insert(0,str(V1))
from model import points
CFG=json.loads((V1/'results/candidate/candidate_B.json').read_text(encoding='utf-8'))

def header():
    return 'simulator lang=spectre\nglobal 0\n'+''.join(f'ahdl_include "{p.name}"\n' for p in sorted(BLOCKS.glob('*.va')))+'''\nparameters vddval=1.2
VDD (vdd 0) vsource dc=vddval
simulatorOptions options reltol=1e-5 vabstol=1e-7 iabstol=1e-13 temp=27
'''

def write(name,body,reltol='1e-5'):
    p=HERE/'tb'/f'{name}.scs';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text((header()+body).replace('reltol=1e-5',f'reltol={reltol}'),encoding='utf-8',newline='\n')

TOP='''
VREF (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n
VN (target 0) vsource dc={n}
VM (ratio 0) vsource dc={m}
VDIST (dist 0) vsource dc=0
XREF (ref refb vdd 0) reference_buffer
XBIAS (vdd 0 vmid) bias_control
XVCO (ctrl code dist vmid vp vn vcoclk fvco vdd 0) lc_vco points_per_cycle={ppc}
XPD (refb vp vn sample pulse vdd 0) subsampling_detector
XCP (sample pulse enable ctrl vdd 0) charge_pump
XLF (ctrl vc1 enable preset 0) loop_filter
XFLL (refb vcoclk target sample vmid code preset enable status locked measured vdd 0) auxiliary_fll
XDIV (vcoclk ratio enable div vdd 0) even_divider
XRT (div vcoclk enable retimed violations vdd 0) output_retimer
XOUT (retimed out vdd 0) output_buffer
CLOAD (out 0) capacitor c=10f
XMEAS (out refb vp vn ctrl freqout dutyout edgecount phaseerr vmax vmin vdd 0) pll_monitor start=20u
tran tran stop={stop} errpreset=conservative strobeperiod=10n strobeoutput=strobeonly
save ctrl vc1 code enable status locked measured sample fvco freqout dutyout edgecount phaseerr violations vmax vmin
saveOptions options save=selected
'''

def main():
    for p in points(CFG):
        write(f'top_k{p["k"]}',TOP.format(**p,ppc=16,stop='25u'))
    write('top_k41_accuracy',TOP.format(n=164,m=4,ppc=32,stop='25u'),reltol='2e-7')
    write('top_k41_recovery',TOP.format(n=164,m=4,ppc=16,stop='40u').replace('VDIST (dist 0) vsource dc=0','VDIST (dist 0) vsource type=pwl wave=[0 0 20u 0 20.00002u -0.024]').replace('start=20u','start=38u'))
    write('top_retune',TOP.format(n=126,m=14,ppc=16,stop='40u').replace('VN (target 0) vsource dc=126','VN (target 0) vsource type=pwl wave=[0 126 20u 126 20.00002u 164]').replace('VM (ratio 0) vsource dc=14','VM (ratio 0) vsource type=pwl wave=[0 14 20u 14 20.00002u 4]').replace('start=20u','start=38u'))
    write('tb_vco','''
VC (ctrl 0) vsource dc=.7
VB (code 0) vsource dc=127
VD (dist 0) vsource dc=0
VBIAS (vmid 0) vsource dc=.6
XV (ctrl code dist vmid vp vn clk fmon vdd 0) lc_vco
tran tran stop=20n errpreset=conservative
save vp vn clk fmon
saveOptions options save=selected
''')
    write('tb_reference','''
VI (inp 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20n rise=10p fall=10p delay=1n
XR (inp out vdd 0) reference_buffer
tran tran stop=200n errpreset=conservative maxstep=200p
save inp out
saveOptions options save=selected
''')
    write('tb_detector','''
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20n rise=10p fall=10p delay=1n
VP (vp 0) vsource dc=.7
VN (vn 0) vsource dc=.5
XP (ref vp vn sample pulse vdd 0) subsampling_detector
tran tran stop=130n errpreset=conservative maxstep=100p
save ref sample pulse
saveOptions options save=selected
''')
    write('tb_cp','''
VS (sample 0) vsource dc=.2
VP (pulse 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=2.073333333333n rise=10p fall=10p delay=2n
VE (en 0) vsource dc=1.2
XC (sample pulse en out vdd 0) charge_pump
VR (out 0) vsource dc=.6
tran tran stop=130n errpreset=conservative maxstep=100p
save pulse VR:p
saveOptions options save=selected
''')
    write('tb_filter','''
VE (en 0) vsource dc=1.2
VP (pre 0) vsource dc=.6
XF (ctrl vc1 en pre 0) loop_filter
IIN (0 ctrl) isource type=pulse val0=0 val1=1u delay=1n rise=10p fall=10p width=100n period=1u
IIN2 (0 ctrl2) isource type=pulse val0=0 val1=1u delay=1n rise=10p fall=10p width=100n period=1u
R (ctrl2 vc12) resistor r=22222.2222222222
C1 (vc12 0) capacitor c=28.6478897565412p
C2 (ctrl2 0) capacitor c=1.90985931710274p
ic ctrl=.6 vc1=.6 ctrl2=.6 vc12=.6
tran tran stop=300n errpreset=conservative maxstep=100p
save ctrl vc1 ctrl2 vc12
saveOptions options save=selected
''')
    for m in [4,6,8,10,12,14]:
        write(f'tb_divider_m{m}',f'''
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period=250p width=123p rise=2p fall=2p delay=20p
VM (ratio 0) vsource dc={m}
VE (en 0) vsource dc=1.2
XD (clk ratio en out vdd 0) even_divider
tran tran stop=50n errpreset=conservative maxstep=10p
save clk out
saveOptions options save=selected
''')
    for delay,label in [('50p','nominal'),('115p','setup_failure')]:
        write(f'tb_retimer_{label}',f'''
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period=250p width=123p rise=2p fall=2p delay=20p
VM (ratio 0) vsource dc=4
VE (en 0) vsource dc=1.2
XD (clk ratio en data vdd 0) even_divider td={delay}
XR (data clk en out violations vdd 0) output_retimer
tran tran stop=50n errpreset=conservative maxstep=10p
save clk data out violations
saveOptions options save=selected
''')
    write('tb_output','''
VI (inp 0) vsource type=pulse val0=0 val1=1.2 period=1n width=490p rise=10p fall=10p delay=20p
XO (inp out vdd 0) output_buffer
CL (out 0) capacitor c=10f
tran tran stop=20n errpreset=conservative maxstep=10p
save inp out
saveOptions options save=selected
''')
    write('tb_bias','''
XB (vdd 0 vmid) bias_control
tran tran stop=1n
save vmid
saveOptions options save=selected
''')
    # FLL independently receives a fixed known VCO frequency; validates finite count and search endpoint.
    write('tb_fll','''
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20n rise=10p fall=10p delay=1n
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period=333.333333333333p width=164.666666666667p rise=2p fall=2p delay=20p
VT (target 0) vsource dc=125
VS (sample 0) vsource dc=0
VBIAS (vmid 0) vsource dc=.6
XF (ref clk target sample vmid code preset en status locked measured vdd 0) auxiliary_fll
tran tran stop=8u errpreset=conservative strobeperiod=10n strobeoutput=strobeonly
save code preset en status locked measured
saveOptions options save=selected
''')
    center=4e9/math.sqrt(1+6/255*((4e9/2.64e9)**2-1))
    control=.6+(3.936e9-center)/20e6
    initial=(.1/(2*math.pi)-3.936e9*1.065e-9)%1
    write('tb_mainloop',f'''
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20n rise=10p fall=10p delay=1n
XR (ref refb vdd 0) reference_buffer
XB (vdd 0 vmid) bias_control
VCODE (code 0) vsource dc=6
VDIST (dist 0) vsource dc=0
VEN (en 0) vsource dc=1.2
VPRE (pre 0) vsource dc={control:.16g}
XV (ctrl code dist vmid vp vn clk fmon vdd 0) lc_vco phase_initial={initial:.16g}
XP (refb vp vn sample pulse vdd 0) subsampling_detector
XC (sample pulse en ctrl vdd 0) charge_pump
XF (ctrl vc1 en pre 0) loop_filter
XM (clk refb vp vn ctrl fm dm em phaseerr vmax vmin vdd 0) pll_monitor start=0
ic ctrl={control:.16g} vc1={control:.16g}
tran tran stop=6u errpreset=conservative strobeperiod=41.6666666666667n strobedelay=1.066n strobeoutput=strobeonly
save ctrl vc1 phaseerr
saveOptions options save=selected
''')
    print('Generated',len(list((HERE/'tb').glob('*.scs'))),'testbenches')

if __name__=='__main__':main()
