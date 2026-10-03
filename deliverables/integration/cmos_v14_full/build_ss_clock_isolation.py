"""Diagnostic only: expose complementary clock ports and remove their drivers.

Ideal internal clocks isolate storage/data-path timing from clock-tree distortion.
This is not an all-transistor PLL implementation or a power/noise result.
"""
from pathlib import Path
import re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
name='bank_clock_isolation_v14'
s=(B/'cmos_even_bank_acq_v14.scs').read_text().replace('cmos_even_bank_acq_v14',name)
s=s.replace('out fllclk vdd vss)','out fllclk ck ckb vdd vss)')
removed=[];lines=[]
for line in s.splitlines():
 if re.match(r'X(?:CI|GN|CB1|CB2|CKB) ',line):removed.append(line)
 else:lines.append(line)
assert len(removed)==5
(B/(name+'.scs')).write_text('\n'.join(lines)+'\n')
for m,rf in [(6,3888e6),(10,3120e6),(14,3024e6)]:
 s=(H/'tb'/f'bankrt_m{m}_ss.scs').read_text().replace('cmos_even_bank_acq_v14',name)
 s=s.replace('q1 predata acqclk vdd 0)','q1 predata acqclk ck ckb vdd 0)')
 period=2/rf;edge=20e-12;width=period/2-edge
 s+=f'\nVCK (ck 0) vsource type=pulse val0=0 val1=1.2 period={period:.17g} rise={edge:.17g} fall={edge:.17g} width={width:.17g}\n'
 s+=f'VCKB (ckb 0) vsource type=pulse val0=1.2 val1=0 period={period:.17g} rise={edge:.17g} fall={edge:.17g} width={width:.17g}\n'
 s=s.replace('stop=100n outputstart=60n','stop=100n')
 # Port aliases are top-level nodes in Spectre save statements.
 s=s.replace('XD.ck XD.ckb','ck ckb')
 s+='save XD.XD6.clkb XD.XD6.X0.qm XD.XD6.X0.XM.x XD.XD6.X0.XS.x\n'
 (H/'tb'/f'bankclkideal_m{m}_ss.scs').write_text(s)
print('Three diagnostic ideal-complementary-clock TBs generated; not PLL acceptance.')
