from pathlib import Path
import re,json
H=Path(__file__).resolve().parent
s=(H/'tb/tb_joint_timing_center.scs').read_text()
fit=H/'results/safe_gain_fit.json'
center=json.loads(fit.read_text())['interpolated_center_deg'] if fit.exists() else 217.45
for tag,phase in [('lo',217.43),('hi',217.47),('center',center)]:
 t=re.sub(r'sinephase=217\.869884783412',f'sinephase={phase}',s)
 t=re.sub(r'sinephase=397\.869884783412',f'sinephase={phase+180}',t)
 if tag!='center':t=re.sub(r'pn pnoise .*\n','',t)
 (H/'tb'/f'tb_joint_safe_{tag}.scs').write_text(t)
