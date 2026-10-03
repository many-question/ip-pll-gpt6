"""Matched-offset fresh-PSS precision screen; no six-point RMS estimate."""
from pathlib import Path
import hashlib
import json
import argparse
import numpy as np
from noise_utils import parse, header, devices, cross

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
R = ROOT / 'research/runs/spectre_cmos_v14_full'
parser=argparse.ArgumentParser();parser.add_argument('--factor',type=int,choices=[2,4],default=2)
args=parser.parse_args();factor=args.factor
protocol = json.loads((H/f'results/rt{factor}_precision_protocol.json').read_text())
freq = np.array(protocol['offsets_hz'])
rows = []
for item in protocol['cases']:
    case = item['case']; j = R/protocol['run']/case
    if not (j/'result.json').exists(): continue
    r = json.loads((j/'result.json').read_text())
    if not r.get('local_outputs_sha256'): continue
    row = dict(case=case, source_result=(j/'result.json').relative_to(ROOT).as_posix(),
               source_sha256=hashlib.sha256((j/'result.json').read_bytes()).hexdigest(), valid=False)
    rows.append(row)
    if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text(): continue
    assert r['remote_inputs_match'] and not r.get('periodic_state')
    raw = j/(case+'.raw'); p = raw/'pnMedge.0.sample.pnoise'
    pn = parse(p); td = parse(raw/'pss.td.pss'); fd = parse(raw/'pss.fd.pss')
    assert np.allclose(pn['freq'], freq, rtol=1e-10, atol=0)
    t = td['time']; T = t[-1]-t[0]; e = cross(t, td['out'])
    periods = np.diff(np.r_[e, e[0]+T]) if len(e) else np.array([0.])
    expected = dict(vp=24,clk=24,q1=12,data=6,out=6,acqclk=6)
    harmonics = {k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in expected}
    endpoint = max(float(abs(td[k][-1]-td[k][0])) for k in expected)
    periodic = bool(abs(T*164e6-1)<1e-7 and len(e)==6 and harmonics==expected
                    and max(abs(periods*984e6-1))<.02 and endpoint<1e-3)
    dev = devices(p, len(freq)); sv = pn['out']**2; slew = header(p,'slew rate event_1')
    err = float(max(abs(sum(dev.values())/sv-1)))
    row.update(valid=periodic and err<1e-7 and slew>0, periodic_passed=periodic,
               harmonics=harmonics, endpoint_max_v=endpoint, slew_v_per_s=slew,
               timing_psd_s2_per_hz=(sv/slew**2).tolist(), device_sum_relative_error=err,
               physical_inputs={k:v for k,v in r['inputs_sha256'].items() if k!=case+'.scs'},
               fresh_pss=True, pnoise_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
out = dict(scope=__doc__, offsets_hz=freq.tolist(), cases=rows,
           complete=len(rows)==2, passed=None, full_band_integral=False, full_pll_acceptance=False)
if len(rows)==2 and all(r['valid'] for r in rows):
    assert rows[0]['physical_inputs']==rows[1]['physical_inputs']
    delta=10*np.log10(np.array(rows[1]['timing_psd_s2_per_hz'])/rows[0]['timing_psd_s2_per_hz'])
    out.update(fine_minus_coarse_psd_db=delta.tolist(), max_absolute_delta_db=float(max(abs(delta))),
               passed=bool(max(abs(delta))<protocol['pointwise_pass_limit_db']))
(H/f'results/rt{factor}_precision_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='cases'},indent=2))
