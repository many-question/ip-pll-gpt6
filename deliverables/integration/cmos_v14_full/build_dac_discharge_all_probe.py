"""Also discharge the six inverter storage nodes left floating when DAC vd is off."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=B/'dac_discharge_v14.scs';s=src.read_text().replace('dac_discharge_v14','dac_discharge_all_v14')
extra='\n'.join(f'MDISB{i} (b{i} enable vss vss) nch w=1u l=1u ad=1u*240n as=1u*240n pd=2*(1u+240n) ps=2*(1u+240n)' for i in range(6))
s=s.replace('ends dac_discharge_all_v14',extra+'\nends dac_discharge_all_v14')
dest=B/'dac_discharge_all_v14.scs';assert not dest.exists();dest.write_text(s)
p=json.loads((H/'results/dac_discharge_protocol.json').read_text())
p.update(scope=__doc__,run='dacdischargeall01',time=datetime.datetime.now().astimezone().isoformat(),candidate_sha256=sha(dest),candidate_file=dest.name,
    hypothesis='Rail-only discharge leaves low-input inverter b nodes floating. Six further enable-controlled NMOS devices establish their off state.',
    physical_change='Seven1um/1um PDK NMOS clamps: vd andsix b nodes toground, allgates=enable. No physical changes to active DAC resistors/header/outputstages/filter.')
p['working_limits']['off_internal_max_v']=.001
for c in p['cases']:
    old=H/'tb'/(c['case']+'.scs');c['case']=c['case'].replace('dac_discharge_','dac_discharge_all_')
    body=old.read_text().replace('dac_discharge_v14','dac_discharge_all_v14')
    body+='\nsave XO.b1 XO.b2 XO.b5 XN.b1 XN.b2 XN.b5\n'
    tb=H/'tb'/(c['case']+'.scs');assert not tb.exists();tb.write_text(body);c['tb_sha256']=sha(tb)
(H/'results/dac_discharge_all_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(' '.join(x['case'] for x in p['cases']))
