"""Measure local deterministic divider/retimer lines; no complete-PLL spur claim."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,cross
from spur_utils import line_metrics,project_lines
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
fixture=json.loads((H/'results/spur_method_validation.json').read_text());assert fixture['passed']
cases=[('chainnoisefine01','chain_noise_fine_tt',1,'fine')]
cases += [(f'rt{f}precision01',f'chain_rt{f}_precision_{p}_tt',f,p) for f in [2,4] for p in ['coarse','fine']]
rows=[]
for run,case,factor,precision in cases:
    j=R/run/case;rp=j/'result.json';r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
    assert r['ok'] and r['remote_inputs_match'] and not r.get('periodic_state')
    assert 'spectre completes with 0 errors' in log and 'pss: The steady-state solution was achieved' in log
    raw=j/(case+'.raw');fp=raw/'pss.fd.pss';tp=raw/'pss.td.pss'
    fd=parse(fp);td=parse(tp);t=td['time'];fund=164e6;fc=984e6
    assert abs((t[-1]-t[0])*fund-1)<1e-7
    assert len(cross(t,td['out']))==6
    assert abs(td['out'][-1]-td['out'][0])<1e-3
    m=line_metrics(fd['freq'],fd['out'],fc)
    frequencies=np.asarray([x['frequency_hz'] for x in m['lines']]+[fc])
    projected=project_lines(t,td['out'],frequencies,fund)
    ratio=abs(projected[:-1])/abs(projected[-1]);reported=np.asarray([x['amplitude_ratio'] for x in m['lines']])
    error=float(max(abs(ratio-reported)))
    strong=reported>10**(-90/20)
    strong_error=float(max(abs(20*np.log10(ratio[strong]/reported[strong])))) if any(strong) else 0.
    row=dict(run=run,case=case,factor=factor,precision=precision,source_result=rp.relative_to(ROOT).as_posix(),
        source_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),fd_sha256=hashlib.sha256(fp.read_bytes()).hexdigest(),
        td_sha256=hashlib.sha256(tp.read_bytes()).hexdigest(),metric=m,
        td_fd_carrier_normalized_line_error=error,td_fd_strong_line_max_delta_db=strong_error,
        quadrature_consistent=bool(error<1e-5 and strong_error<.2),full_pll_acceptance=False)
    rows.append(row)
numerical=[]
for factor in [2,4]:
    coarse=next(x for x in rows if x['factor']==factor and x['precision']=='coarse')
    fine=next(x for x in rows if x['factor']==factor and x['precision']=='fine')
    a=coarse['metric']['lines'];b=fine['metric']['lines'];assert [x['offset_hz'] for x in a]==[x['offset_hz'] for x in b]
    deltas=[y['dbc']-x['dbc'] for x,y in zip(a,b)]
    strong=[i for i,(x,y) in enumerate(zip(a,b)) if max(x['dbc'],y['dbc'])>-90]
    numerical.append(dict(factor=factor,fine_minus_coarse_line_db=deltas,
        max_strong_line_delta_db=max(abs(deltas[i]) for i in strong),
        strong_lines_converged=all(abs(deltas[i])<.2 for i in strong)))
out=dict(scope=__doc__,cases=rows,numerical_comparisons=numerical,full_pll_acceptance=False,requirement_met=None,
    condition='TT27/1.2V/984MHz/10fF,noiselessRFreplay,actualRX/fullbank/retimer/quietcounter;fund164MHz.',
    limitation='Only intrinsic local164MHz-grid lines are represented. No24MHz reference, LC sampled loop, or slow-control modulation; cannot test completePLLREQ07 or establish absence of lower-offset lines.',
    criterion_status='10kHz-fout/2 range proposed, not confirmed; no change to hardREQ07.',
    tests='Analytic AM/PM/one-sideband controls; successful freshPSS; direct time-domain quadrature; own coarse/fine matched circuits.')
(H/'results/local_chain_spur_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(cases=[dict(case=x['case'],largest=x['metric']['largest_line'],quadrature=x['quadrature_consistent']) for x in rows],numerical=numerical),indent=2))
