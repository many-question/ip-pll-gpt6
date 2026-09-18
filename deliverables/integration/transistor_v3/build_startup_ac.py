"""Small-signal differential driving-point admittance at the symmetric DC point."""
from pathlib import Path
import json,re
H=Path(__file__).resolve().parent
for tag,source in [('q5_base','tb_rlc_q5_c255_nom'),('q5_wide','tb_rlc_q5_c255_wide'),('q5_current','tb_rlc_q5_c255_current'),('q8_base','tb_rlc_q8_c255_nom'),('q5_high','tb_rlc_q5_c0_nom')]:
 s=(H/'tb'/f'{source}.scs').read_text()
 s=re.sub(r'ic vp=.*\n','',s)
 s=re.sub(r'tran tran .*\n','IP (0 vp) isource dc=0 mag=1\nIN (vn 0) isource dc=0 mag=1\nac ac start=1.5G stop=5G lin=701\n',s)
 (H/'tb'/f'tb_startup_ac_{tag}.scs').write_text(s)
