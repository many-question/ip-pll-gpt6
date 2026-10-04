"""Prepare fresh-PSS edge and independent noise-on checks for the repaired bank."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/rt_pulsetrip_noise_validation.json').read_text())
row=next(x for x in v['cases'] if x['factor']==4 and x['grade']=='probe')
assert row['periodic_passed'] and row['device_sum_relative_error']<1e-7
old=json.loads((H/'results/rt4_fine_audit_protocol.json').read_text());groups=old['groups']
base=(H/'tb/chain_rt4_pulsetrip_probe_tt.scs').read_text()
assert 'readpss=' not in base and 'bank_pulsetrip_v14' in base
base=base.replace('values=[10k 100k 1M 10M 100M 491.99M]','values=[1M 100M 491.99M]')
line=next(x for x in base.splitlines() if x.startswith('edge jitterevent'))
edgecase='chain_rt4_pulsetrip_edges_tt'
edges=base.replace('measurement=[edge]','measurement=['+' '.join(f'edge{i}' for i in range(1,7))+']')
edges=edges.replace(line,'\n'.join(line.replace('edge jitterevent',f'edge{i} jitterevent').replace('triggernum=1',f'triggernum={i}') for i in range(1,7)))
gatecases={g:f'chain_rt4_pulsetrip_only_{g}_tt' for g in groups};hashes={}
for case,body in [(edgecase,edges)]+[(gatecases[g],base.replace('temp=27','temp=27 noiseon_inst=['+' '.join(names)+'] noiseon_type=all')) for g,names in groups.items()]:
    target=H/'tb'/(case+'.scs');assert not target.exists();target.write_text(body);hashes[case]=sha(target)
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',factor=4,
    run='rt4pulsetripaudit01',cases=[edgecase]+list(gatecases.values()),gate_cases=gatecases,groups=groups,
    tb_sha256=hashes,bank_sha256=sha(H.parents[1]/'blocks/cmos_v14_full/bank_pulsetrip_v14.scs'),
    source_probe_result=row['source_result'],source_probe_sha256=row['source_sha256'],offsets_hz=old['offsets_hz'],
    noise_gate_relative_limit=old['noise_gate_relative_limit'],edge_spread_limit_db=old['edge_spread_limit_db'],
    condition='Repairedbank+RT4,TT27/1.2V/984MHz/10fF,noiselesszeroimpedanceRFreplay,.5ps/767/maxac504GHz; fresh PSS for every case.',
    launch_gate='Review new-bank probe and full-band progress; use a released one-thread long slot. No automatic launch or overlap with method controls.',
    full_band_integral=False,full_pll_acceptance=False,main_dut_modified=False)
(H/'results/rt4_pulsetrip_audit_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(status=out['status'],cases=out['cases']),indent=2))
