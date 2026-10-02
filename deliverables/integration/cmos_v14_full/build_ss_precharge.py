"""Single-phase divider test with a longer precharge interval."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
name='cmos_even_bank_precharge_v14'
s=(B/'cmos_even_bank_singlephase_v14.scs').read_text().replace('cmos_even_bank_singlephase_v14',name)
s=s.replace('XCKB (ck ckb vdd vss) pll_inv wn=8u wp=16u',
            'XCKB (ck ckb vdd vss) pll_inv wn=24u wp=48u')
s=s.replace('XD6 (ck d6','XD6 (ckb d6').replace('XRL (reset ck loadb','XRL (reset ckb loadb')
s=s.replace(' ck ckb load loadb ',' ckb ck load loadb ')
(B/(name+'.scs')).write_text(s)
for p in (H/'tb').glob('bankclksp_m*.scs'):
 s=p.read_text().replace('cmos_even_bank_singlephase_v14',name)
 (H/'tb'/p.name.replace('bankclksp_','bankclkpre_')).write_text(s)
