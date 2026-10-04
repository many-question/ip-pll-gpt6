"""Reduce only the analytic linear-RC calibration grid; preserve MOS full-band tests."""
from pathlib import Path
import datetime,hashlib,json,math
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=H/'results/core_noise_calibration_protocol.json';p=json.loads(old.read_text())
cancel=ROOT/'research/runs/spectre_cmos_v14_full/corecal01/noise_core_cal_core/cancellation.json';assert cancel.exists()
offsets=[1e4,1e6,2e6,1e7,1e8,492e6];rows=[]
for oldcase in p['cases']:
    original=H/'tb'/(oldcase['case']+'.scs');body=original.read_text()
    assert body.count('start=10k stop=492M dec=20')==1
    body=body.replace('start=10k stop=492M dec=20','values=[10k 1M 2M 10M 100M 492M]')
    case=oldcase['case'].replace('noise_core_cal_','noise_core_cal6_');target=H/'tb'/(case+'.scs');assert not target.exists();target.write_text(body)
    rows.append(dict(oldcase,case=case,tb_sha256=sha(target)))
rho=math.exp(-1/(p['sample_frequency_hz']*p['resistance_ohm']*p['capacitance_f']))
p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='corecal6_01',cases=rows,
    offsets_hz=offsets,output='core_noise_calibration_sparse_validation.json',
    original_protocol_sha256=sha(old),original_cancellation_sha256=sha(cancel),
    analytic_rho=rho,analytic_relative_psd_ripple_bound=4*rho/(1-rho)**2,
    change='Only the frequency grid changes from dec20 to six explicit controls. Both band endpoints and2MHz automatic-Jee boundary are measured. Fresh PSS remains mandatory.',
    launch_gate='After rt4c24tune01 single point completes and is collected, reuse the one-thread shortslot. Two sequential RC cases; no further automatic batch.',
    why_sparse_suffices_for_this_fixture='Exact stationaryRC sampled covariance has rho~8.55e-23; its PSD relative ripple is bounded above by4e-22. Trapezoidal integration of this known flat thermal-noise fixture calibrates normalization. This argument does not apply to MOS flicker or arbitrary colored noise.',
    limits=dict(p['limits'],point_psd_db_to_analytic=.1),
    limitations=p['limitations']+['Sparse fixture frequency controls are not a replacement for the actual-MOS full-band integral or harmonic-neighbour checks.'])
(H/'results/core_noise_calibration_sparse_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(' '.join(x['case'] for x in rows))
