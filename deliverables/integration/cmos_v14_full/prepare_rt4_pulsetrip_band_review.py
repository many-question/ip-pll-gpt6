"""Select RT4 after both new-bank probes and add finite harmonic-neighbour checks."""
from pathlib import Path
import datetime,hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
path=H/'results/rt_pulsetrip_noise_protocol.json';p=json.loads(path.read_text());v=json.loads((H/'results/rt_pulsetrip_noise_validation.json').read_text())
rows=sorted([x for x in v['cases'] if x['grade']=='probe'],key=lambda x:x['factor'])
assert v['probe_complete'] and len(rows)==2 and all(x['periodic_passed'] and x['device_sum_relative_error']<1e-7 for x in rows)
delta=10*np.log10(np.array(rows[1]['timing_psd_s2_per_hz'])/rows[0]['timing_psd_s2_per_hz']);assert max(delta)<-2
item=next(x for x in p['cases'] if x['factor']==4 and x['grade']=='band')
assert not (ROOT/'research/runs/spectre_cmos_v14_full'/item['run']).exists()
tb=H/'tb'/(item['case']+'.scs');assert sha(tb)==item['tb_sha256'];original=tb.read_text()
archive=H/'tb/chain_rt4_pulsetrip_band_logonly_unrun_tt.scs';assert not archive.exists();archive.write_text(original)
near=sorted({int(center+sign*distance) for center in [164e6,328e6,492e6] for distance in [1,10,100,1000,10000] for sign in [-1,1] if 1e4<=center+sign*distance<=492e6})
extra='\n// Finite offsets around shifted flicker poles; no assumed low-frequency cutoff.\n'
extra+='pnnear pnoise values=['+' '.join(map(str,near))+'] pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=6 maxsideband=767\n'
tb.write_text(original+extra)
item.update(tb_sha256=sha(tb),unrun_log_grid_only_source=archive.relative_to(ROOT).as_posix(),unrun_log_grid_only_source_sha256=sha(archive),harmonic_neighbour_offsets_hz=near,
    change='Same repaired physical divider; original full-band grid plus25finite harmonic-neighbour offsets under the same fresh PSS. Exact endpoint retained.')
p['band_selection_review']=dict(time=datetime.datetime.now().astimezone().isoformat(),selected_factor=4,selected_run=item['run'],
    source_results=[dict(path=x['source_result'],sha256=x['source_sha256']) for x in rows],rt4_minus_rt2_psd_db=delta.tolist(),
    rationale='All six matched new-bank offsets favourRT4 by2.895..3.194dB; period and device sums pass. Use the released one-thread probe slot forRT4fullband first.',
    limits='Not actualLC or fullPLL; original-grid RMS remains provisional until shifted flicker poles, all-edge/numerical precision, new noise-only gates and PVT close. No automaticRT2band or main-DUT adoption.')
path.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(p['band_selection_review'],indent=2))
