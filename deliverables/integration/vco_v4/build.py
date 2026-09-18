"""Generate explicitly parameterized VCO repair experiments; never modify v3."""
from pathlib import Path
import json, re
import numpy as np
from scipy.optimize import brentq

H=Path(__file__).resolve().parent
B=H.parents[1]/'blocks/vco_v4'
OLD=H.parent/'transistor_v3'
MODEL='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'

def rs_fit(l,q=5,cscale=1):
    w=2*np.pi*3.3e9
    def z(r):
        sub=1/(1/300+1j*w*50e-15*cscale)
        return 1/(1/(r+1j*w*l)+1j*w*20e-15*cscale+1/(1/(1j*w*80e-15*cscale)+sub))
    return brentq(lambda r:z(r).imag/z(r).real-q,.01,50)

def blocks():
    B.mkdir(parents=True,exist_ok=True)
    core=(B.parent/'transistor_v3/lc_core_rlc.scs').read_text().replace('tx_lc_core_rlc','tx_lc_core_v4n')
    (B/'lc_core_v4n.scs').write_text(core)
    comp=core.replace('tx_lc_core_v4n','tx_lc_core_v4c').replace('cscale=1','cscale=1 pcore_w=80u')
    comp=comp.replace('XP (vdd vp','XP (ct vp').replace('XN (vdd vn','XN (ct vn')
    pos=comp.index('MT (')
    comp=comp[:pos]+'''// Complementary current reuse. CT floats at the circuit's own common mode.
MP0 (vp vn vdd vdd) pch w=pcore_w l=180n ad=pcore_w*240n as=pcore_w*240n pd=2*(pcore_w+240n) ps=2*(pcore_w+240n)
MP1 (vn vp vdd vdd) pch w=pcore_w l=180n ad=pcore_w*240n as=pcore_w*240n pd=2*(pcore_w+240n) ps=2*(pcore_w+240n)
'''+comp[pos:]
    (B/'lc_core_v4c.scs').write_text(comp)
    for k in ['n','c']:
        s=f'''simulator lang=spectre
include "inductor_pi.scs"
include "lc_core_v4{k}.scs"
include "cap_bank_experiment.scs"
// Q and parasitics are provisional RLC assumptions. Bias reference stays ideal.
subckt tx_lc_vco_v4{k} (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vdd vss)
parameters fixed_c=20f tank_l=1.6n series_r=5 cscale=1 core_w=80u pcore_w=80u ibias=80u unit_c=6.5f unit_w=2.4u fine_w=3u
XL (vp vn vdd vss) tx_lc_core_v4{k} tank_l=tank_l tank_r=series_r tank_c=fixed_c core_w=core_w ibias=ibias cscale=cscale{(' pcore_w=pcore_w' if k=='c' else '')}
XBP (vp b0 b1 b2 b3 b4 b5 b6 b7 vss) tx_cap_bank_experiment unit_c=unit_c unit_w=unit_w
XBN (vn b0 b1 b2 b3 b4 b5 b6 b7 vss) tx_cap_bank_experiment unit_c=unit_c unit_w=unit_w
CVP (vp ctrl) nmoscap lr=2u wr=fine_w mr=1
CVN (vn ctrl) nmoscap lr=2u wr=fine_w mr=1
ends tx_lc_vco_v4{k}
'''
        (B/f'lc_vco_v4{k}.scs').write_text(s)

def bench(name, kind='n', code=0, ctrl=.6, corner='tt', temp=None, loaded=False, m=4,
          l=1.6e-9, q=5, cscale=1, core=80e-6, pcore=80e-6, ibias=80e-6,
          fixed=20e-15, unit=6.5e-15, switch=2.4e-6, fine=3e-6, proxy=0,
          stop=300e-9, step=5e-12, seed=1e-5, analysis='tran', fund=3.5e9, sidebands=31):
    if temp is None:temp={'tt':27,'ss':60,'ff':0}[corner]
    args=dict(locals());args.pop('temp',None);args['temp']=temp
    rs=rs_fit(l,q) # C sensitivity holds fitted metal loss fixed.
    args['series_r_ohm']=rs
    s=f'''simulator lang=spectre
global 0
include "{MODEL}" section={corner}
include "{MODEL}" section=stat_noise
simulator lang=spectre insensitive=no
include "{MODEL}" section={corner}_bbmvar
simulator lang=spectre insensitive=no
include "cells.scs"
simulatorOptions options reltol=1e-5 vabstol=1e-7 iabstol=1e-13 temp={temp}
include "lc_vco_v4{kind}.scs"
VDD (vdd 0) vsource dc=1.2
VVCO (vco_vdd vdd) vsource dc=0
VC (ctrl 0) vsource dc={ctrl}
'''
    s+=''.join(f'VB{i} (b{i} 0) vsource dc={1.2 if code&(1<<i) else 0}\n' for i in range(8))
    s+=f'XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vco_vdd 0) tx_lc_vco_v4{kind} fixed_c={fixed:.14g} tank_l={l:.14g} series_r={rs:.14g} cscale={cscale} core_w={core:.14g} pcore_w={pcore:.14g} ibias={ibias:.14g} unit_c={unit:.14g} unit_w={switch:.14g} fine_w={fine:.14g}\n'
    extra=''
    if loaded:
        old=(OLD/'tb/tb_rlc_loaded_c255_lo.scs').read_text()
        load=old[old.index('include "divider_v2'):old.index('ic vp=')]
        selected=['vdd' if x==m else '0' for x in [4,6,8,10,12,14]]
        load=re.sub(r'XD \(.*\) tx_divider_bank_light',f'XD (vp vn rst {" ".join(selected)} out vdd 0) tx_divider_bank_light',load)
        s+=load
        extra=' out XD.selected XD.icp XD.icn sp sn hp hn VO:p'
    elif proxy:
        s+=f'CPROX (vp 0) capacitor c={proxy:.14g}\nCNROX (vn 0) capacitor c={proxy:.14g}\n'
    cm=.65 if kind=='c' else 1.2
    if analysis=='ac':
        s+='IP (0 vp) isource dc=0 mag=1\nIN (vn 0) isource dc=0 mag=1\nac ac start=1.5G stop=6G lin=901\n'
    else:
        s+=f'ic vp={cm+seed:.14g} vn={cm}\n'
        if analysis=='tran':s+=f'tran tran stop={stop:.14g} maxstep={step:.14g} errpreset=conservative\n'
        elif analysis=='noise':
            assert not loaded,'Use a synchronous load or QPSS for multiple frequencies'
            s+=f'pss (vp vn) pss fund={fund:.14g} harms=31 tstab={stop:.14g} maxstep={step:.14g} errpreset=conservative saveinit=yes\npn (vp vn) pnoise start=10k stop=500M dec=20 maxsideband={sidebands} noiseout=[usb am pm] sweeptype=relative relharmnum=1\n'
    s+=f'save vp vn XV.XL.tail VDD:p VVCO:p{extra}\nsaveOptions options save=selected\n'
    (H/'tb').mkdir(exist_ok=True)
    (H/'tb'/f'{name}.scs').write_text(s)
    (H/'cases').mkdir(exist_ok=True)
    (H/'cases'/f'{name}.json').write_text(json.dumps(args,indent=2)+'\n')
    return name

def main():
    (H/'results').mkdir(parents=True,exist_ok=True)
    blocks()
    candidates=[('n80',dict(core=80e-6)),('n120',dict(core=120e-6)),
                ('n80i100',dict(core=80e-6,ibias=100e-6)),
                ('c20p40',dict(kind='c',core=20e-6,pcore=40e-6,l=2e-9,unit=5.7e-15)),
                ('c40p80',dict(kind='c',core=40e-6,pcore=80e-6,l=1.6e-9)),
                ('c40p40',dict(kind='c',core=40e-6,pcore=40e-6,l=1.8e-9,unit=6e-15))]
    for tag,p in candidates:
        for code in [0,255]:bench(f'screen_{tag}_c{code}',code=code,proxy=140e-15,stop=160e-9,**p)
if __name__=='__main__':main()
