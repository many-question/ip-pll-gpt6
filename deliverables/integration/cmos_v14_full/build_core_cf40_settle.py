"""Prepare six additional microseconds from CF40's own physical final state."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=ROOT/'research/runs/spectre_cmos_v14_full/corenoisecand01/core_noisecand_cf40_tt';r=json.loads((j/'result.json').read_text())
v=json.loads((H/'results/core_noise_candidates_validation.json').read_text());a=next(x for x in v['cases'] if x['variant']=='cf40')
assert r['ok'] and r['remote_inputs_match'] and sha(j/'result.json')==a['source_sha256']
source=j/'final.ic';assert sha(source)==r['local_outputs_sha256']['final.ic']
lines=[x for x in source.read_text().splitlines() if x.strip() and (x.split()[0].startswith('XP.') or x.split()[0] in ['out','ref','vdd'])]
values={x.split()[0]:float(x.split()[1]) for x in lines}
assert all(abs(values[k]-1.2)<1e-12 for k in ['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd'])
seed=H/'state_inputs/core_cf40_own_seed_tt.ic';assert not seed.exists();seed.write_text('# Actual CF40 own3us final state; observer omitted. Text warm start, not native checkpoint.\n'+'\n'.join(lines)+'\n')
src=H/'tb/core_noisecand_cf40_tt.scs';body=src.read_text()
assert body.count('stop=3u')==1 and body.count('core_pulsetrip_supply_seed_tt.ic')==1
body=body.replace('stop=3u','stop=6u').replace('core_pulsetrip_supply_seed_tt.ic',seed.name)
target=H/'tb/core_cf40_settle6_tt.scs';assert not target.exists();target.write_text(body)
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='corecf40settle01',case=target.stem,
    source_result=a['source'],source_result_sha256=a['source_sha256'],source_final_ic_sha256=sha(source),seed_sha256=sha(seed),candidate_tb_sha256=sha(target),
    retained_state_entries=len(lines),source_stationarity=a['stationarity'],
    change='Same CF40 physical circuit and solver; start from its actual3us final state and observe six further microseconds. Localtime0 matches forcing phase modulo250ns. Observer states omitted; not native continuation.',
    reason='Prior3us CF40 failed only the phase-drift screen: -.015315rad/us versus .01limit. FreeVCO low-offset noise improvement motivates testing longer actual-loop settling before a noise claim.',
    launch_gate='Use a released six-thread long slot only after current PSS review; no automatic launch or extra concurrency.',
    acceptance='Same last1us phasepp<.02rad, absdrift<.01rad/us, RF/outputcycles errors<.001 andcontrol.2..1V; actualcoarse23/supplies and physical dependency hashes must match.',
    limitations=['No random-noise or cold-start result.','CF40 long bias time constant means even a6us warm screen is not final power-up/lowfrequency-noise closure.','2ns observer strobes cannot measure GHz spectra, swing or average supply power.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_cf40_settle_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(case=target.stem,states=len(lines),status=out['status']),indent=2))
