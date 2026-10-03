"""Compare unchanged full-DUT divider with the identical RF replay boundary."""
from pathlib import Path
H=Path(__file__).resolve().parent
for m in [4,6,10]:
 s=(H/'tb'/f'bankboostrf_m{m}_ss.scs').read_text().replace('bank_preboost50_v14','cmos_even_bank_acq_v14').replace('stop=100n outputstart=60n','stop=60n outputstart=20n')
 s=s.replace('XD.ck XD.gn XD.cb','XD.ck XD.ckb')
 (H/'tb'/f'bankrfbase_m{m}_ss.scs').write_text(s)
print('bankrfbase_m4_ss bankrfbase_m6_ss bankrfbase_m10_ss')
