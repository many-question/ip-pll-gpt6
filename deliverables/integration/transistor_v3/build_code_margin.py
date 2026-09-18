"""Locate Q=5 loaded oscillation loss within the required frequency band."""
from pathlib import Path
import re
H=Path(__file__).resolve().parent
def main():
    s=(H/'tb/tb_rlc_loaded_c255_lo.scs').read_text().replace('dc=0.2','dc=0.6')
    for code in [128,160,176,192,224,240]:
        t=s
        for b in range(8):
            t=re.sub(rf'VB{b} \(b{b} 0\) vsource dc=1.2',f'VB{b} (b{b} 0) vsource dc={1.2 if code&(1<<b) else 0}',t)
        (H/'tb'/f'tb_rlc_loaded_c{code}_mid.scs').write_text(t,newline='\n')
if __name__=='__main__':main()
