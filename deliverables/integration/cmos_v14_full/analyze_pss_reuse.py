"""Validate checked PSS state reuse against a fresh analytic RC fixture run."""
from pathlib import Path
import json,hashlib,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;R=H.parents[3]/'research/runs/spectre_cmos_v14_full'
rows=[];spectra=[]
for run in ['psstest01','psstest02']:
 j=R/run/'noise_reuse_fixture';rec=json.loads((j/'result.json').read_text())
 assert rec['ok'] and rec['remote_inputs_match'] and rec.get('local_outputs_sha256')
 assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
 p=j/'noise_reuse_fixture.raw/pnMedge.0.sample.pnoise'
 d=parse_spectre_psf_ascii(p).data;f=np.asarray(d['freq']);v=np.asarray(d['out'])
 slope=float(re.search(r'"slew rate event_1"\s+([0-9.eE+\-]+)',p.read_text())[1]);st=(v/slope)**2
 spectra.append((f,st))
 rows.append(dict(run=run,source_result=(j/'result.json').relative_to(H.parents[3]).as_posix(),source_sha256=hashlib.sha256((j/'result.json').read_bytes()).hexdigest(),periodic_state=rec.get('periodic_state'),jitter_fs=float(np.sqrt(np.trapezoid(st,f))*1e15)))
assert rows[1]['periodic_state']['remote_hash_match'] and rows[1]['periodic_state']['checkpss']=='yes'
assert np.array_equal(spectra[0][0],spectra[1][0])
relative=float(max(abs(spectra[1][1]/spectra[0][1]-1)))
out=dict(scope=__doc__,condition='Same RC calibration:1kohm/20fF,27C,984MHz sine,164MHz PSS,sampleratio6,full10kHz-492MHz sampled integral.',cases=rows,max_relative_psd_change=relative,passed=relative<.001,not_pll_performance=True)
(H/'results/pss_reuse_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
assert out['passed']
