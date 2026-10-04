"""Separate voltage-noise and slew contributions to measured edge-to-edge PSD spread."""
from pathlib import Path
import hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=H/'results/rt4_pulsetrip_audit_validation.json';d=json.loads(source.read_text())
assert d['edge_passed'] and len(d['edge_rows'])==6 and d['fresh_probe_repeat']['passed']
st=np.array([r['psd_s2_per_hz'] for r in d['edge_rows']]);slopes=np.array([r['slew_v_per_s'] for r in d['edge_rows']])
sv=st*slopes[:,None]**2
timedb=10*np.log10(st/st[0]);voltdb=10*np.log10(sv/sv[0]);slewdb=-20*np.log10(slopes/slopes[0])
closure=float(max(abs((timedb-voltdb-slewdb[:,None]).ravel())));assert closure<1e-10
out=dict(scope=__doc__,source_result=d['source_result'],source_sha256=d['source_sha256'],
    edge_raw_noise_sha256=[x['raw_noise_sha256'] for x in d['edge_rows']],offsets_hz=d['offsets_hz'],
    timing_psd_spread_db=np.ptp(timedb,axis=0).tolist(),voltage_noise_psd_spread_db=np.ptp(voltdb,axis=0).tolist(),
    slew_range_v_per_s=[float(min(slopes)),float(max(slopes))],slew_timing_psd_spread_db=float(np.ptp(slewdb)),
    edge_slew_timing_psd_change_db=slewdb.tolist(),edge_voltage_psd_change_db=voltdb.tolist(),decomposition_residual_db=closure,
    interpretation='At these three offsets the small inter-edge timing-PSD spread can be decomposed exactly into measured voltage-noise PSD and the squared-slew conversion. This does not establish behavior at unmeasured offsets, PVT, or the actualLC/fullPLL.',
    full_band_integral=False,full_pll_acceptance=False)
(H/'results/rt4_edge_spread_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if not k.startswith('edge_')},indent=2))
