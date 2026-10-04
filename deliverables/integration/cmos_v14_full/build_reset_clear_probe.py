"""Physical reset-only discharge of the observed weak NAND stack node.

Unit comparison only: no claim that this causes or fixes whole-core PSS.
"""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks';DEST=B/'cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def extract(p,name):
    return re.search(r'^subckt '+name+r' .*?^ends '+name+r'\s*$',p.read_text(),re.M|re.S)[0].rstrip()+'\n'

def main():
    cells=B/'transistor_v1/cells.scs';digital=B/'transistor_v2/digital_cells_v2.scs'
    nand=extract(cells,'pll_nand2').replace('pll_nand2','nand_reset_clear_v14').replace('(a b y vdd vss)','(a b clear y vdd vss)')
    # Put resetb on the upper stack device. During reset it isolates the
    # high output from the new discharge path, including when data is high.
    nand=nand.replace('MN0 (y a x vss)','MN0 (y b x vss)').replace('MN1 (x b vss vss)','MN1 (x a vss vss)')
    nand=nand.replace('ends nand_reset_clear_v14','MCLR (x clear vss vss) nch w=400n l=1u ad=96f as=96f pd=1.28u ps=1.28u\nends nand_reset_clear_v14')
    latch=extract(digital,'tx_latch_r').replace('tx_latch_r','latch_reset_clear_v14').replace('(d gate gateb resetb q vdd vss)','(d gate gateb resetb reset q vdd vss)')
    assert 'XN (x resetb qb vdd vss) pll_nand2' in latch
    latch=latch.replace('XN (x resetb qb vdd vss) pll_nand2','XN (x resetb reset qb vdd vss) nand_reset_clear_v14')
    dff=extract(digital,'tx_dff_r0').replace('tx_dff_r0','dff_reset_clear_v14')
    dff=dff.replace('resetb qm vdd vss) tx_latch_r','resetb reset qm vdd vss) latch_reset_clear_v14').replace('resetb q vdd vss) tx_latch_r','resetb reset q vdd vss) latch_reset_clear_v14')
    assert 'tx_latch_r' not in dff
    out=DEST/'reset_clear_cells_v14.scs';assert not out.exists();out.write_text('simulator lang=spectre\n// Candidate only; original cells are unchanged. Two reset discharge MOS per DFF.\n'+nand+'\n'+latch+'\n'+dff,encoding='utf-8',newline='\n')
    rows=[];T=1/984e6
    for corner,temp in [('tt',27),('ss',60),('ff',0)]:
        case=f'reset_clear_dff_{corner}';dst=H/'tb'/(case+'.scs');assert not dst.exists()
        body=f'''simulator lang=spectre
global 0
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section={corner}
simulator lang=spectre insensitive=no
include "cells.scs"
include "digital_cells_v2.scs"
include "reset_clear_cells_v14.scs"
simulatorOptions options temp={temp} reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VDD (vdd 0) vsource dc=1.2
VC (clk 0) vsource type=pulse val0=0 val1=1.2 period={T:.17g} width={T/2-1e-11:.17g} rise=10p fall=10p delay=200p
VD (d 0) vsource type=pulse val0=0 val1=1.2 period={8*T:.17g} width={4*T-1e-11:.17g} rise=10p fall=10p delay=4.7n
VR (reset 0) vsource type=pwl wave=[0 1.2 3n 1.2 3.01n 0 17.3n 0 17.31n 1.2 20.2n 1.2 20.21n 0 31.4n 0 31.41n 1.2 40n 1.2]
XOLD (d clk reset qo vdd 0) tx_dff_r0
XNEW (d clk reset qn vdd 0) dff_reset_clear_v14
CO (qo 0) capacitor c=2f
CN (qn 0) capacitor c=2f
ic XOLD.XM.XN.x=29.5m XOLD.XS.XN.x=29.5m XNEW.XM.XN.x=29.5m XNEW.XS.XN.x=29.5m
save clk d reset qo qn XOLD.XM.XN.x XOLD.XS.XN.x XNEW.XM.XN.x XNEW.XS.XN.x VDD:p
saveOptions options save=selected
tran tran stop=40n maxstep=1p method=traponly errpreset=conservative
'''
        dst.write_text(body,encoding='utf-8',newline='\n');rows.append(dict(run='resetclearunit01',case=case,corner=corner,temp_c=temp,tb_sha256=sha(dst)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
           condition='1.2V/984MHz clock/10ps clock and data edges/2fF per output; TT27,SS60,FF0; deterministic 29.5mV initial stack node voltage.',
           original_sources_sha256={x.relative_to(ROOT).as_posix():sha(x) for x in [cells,digital]},candidate_sha256=sha(out),
           sample_delay_s=.60*T,input_guard_s=150e-12,engineering_reset_deadline_s=1e-9,engineering_stack_clear_limit_v=.001,
           circuit_change='Resetb moves to upper NAND NMOS; data to lower NMOS. A reset-controlled 0.4um/1um NMOS discharges the isolated stack node.',
           main_dut_modified=False,full_pll_acceptance=False,
           limitations=['One resettable DFF per variant; not the 14-bit counter or complete PLL.',
                        'Three paired PVT points, not a full PVT grid or recovery/removal sweep.',
                        'Deterministic initial-state experiment, no random noise or power-up ramp.',
                        'Eliminating this weakly constrained node does not establish the cause of whole-core PSS failure.'])
    dst=H/'results/reset_clear_unit_protocol.json';assert not dst.exists();dst.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
