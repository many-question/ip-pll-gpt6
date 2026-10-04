"""Audit direct, native and dynamically updated noise activation without adoption."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross,parse,header
from transient_diagnostics import effective,recovery
from analyze_retimer_transient_noise_control import physical,edge_band_power
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/retimer_restart_diagnosis_protocol.json';p=json.loads(pp.read_text())
    sp=H/'results/retimer_transient_noise_protocol.json';s=json.loads(sp.read_text())
    src=ROOT/s['source_result'];assert sha(src)==s['source_sha256']
    sourcebody=(src.parent/'inputs'/(src.parent.name+'.scs')).read_text()
    nf=src.parent/(src.parent.name+'.raw')/'pnMedge.0.sample.pnoise';assert sha(nf)==s['source_noise_sha256']
    pn=parse(nf);basepath=R/'rttrannoiseoff025/retimer_tran_noise_seed_tt';br=json.loads((basepath/'result.json').read_text())
    assert sha(basepath/'waveforms.npz')==br['local_outputs_sha256']['waveforms.npz']
    with np.load(basepath/'waveforms.npz') as z:base=cross(z['time'],z['out'],.6)
    n=1024;fs=984e6;base=base[base>=2e-7][:n];g=edge_band_power(np.zeros(n),fs,5e6,492e6)
    expected=integral(pn['freq'],pn['out']**2/header(nf,'slew rate event_1')**2,g['lower'],g['upper'])
    cases=[('rttrannoise80g05','retimer_tran_noise_seed_tt','native activation'),
        ('rtnoisevabstol01','retimer_tran_noise_seed_tt','native + dynamic1nV to100nV'),
        ('rtvabon80g05','retimer_tran_noise_vab100_seed_tt','native static100nV'),
        ('rtnoisedirect01','retimer_tran_noise_direct_tt','direct noise from t0'),
        ('rtnoisedynamicnoop01','retimer_tran_noise_seed_tt','native + dynamic1nV to1nV'),
        ('rtnoiseenableevent01','retimer_tran_noise_seed_tt','native + explicit isnoisy event'),
        ('rtnoisestart01','retimer_tran_noise_seed_tt','native + explicit100ns analysis start'),
        ('rtnoiseiniton02','retimer_tran_noise_epsilon_seed_tt','native from1e-6-noise seed, restored physical noise scale1')]
    rows=[]
    for run,case,label in cases:
        j=R/run/case;rp=j/'result.json';row=dict(run=run,case=case,condition=label,completed=False);rows.append(row)
        if not rp.exists():continue
        r=json.loads(rp.read_text());lp=j/'spectre.out';log=lp.read_text()
        row.update(source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),log_sha256=sha(lp),
                   recovery=recovery(log),effective_initial=effective(log),solver_overrides=r.get('transient_solver_overrides',{}))
        assert r['remote_inputs_match'] and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=case+'.scs'}==s['dependencies_sha256']
        assert physical((j/'inputs'/(case+'.scs')).read_text())==physical(sourcebody)
        if r.get('native_state'):assert r['native_state']['sha256']==sha(ROOT/r['native_state']['local'])
        if not r['ok'] or not r.get('local_outputs_sha256'):row['errors']=r.get('errors');continue
        cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:
            t0,y0=float(z['time'][0]),float(z['out'][0]);e=cross(z['time'],z['out'],.6)
        boundary_ok=None
        if r.get('native_state'):
            old=R/r['native_state']['source_snapshot']/case/'waveforms.npz'
            with np.load(old) as z:
                index=int(np.argmin(abs(z['time']-t0)));assert abs(z['time'][index]-t0)<1e-15
                previous=float(z['out'][index])
            boundary_ok=abs(y0-previous)<1e-3
            row['native_boundary']=dict(passed=boundary_ok,time_s=t0,expected_output_v=previous,observed_output_v=y0,
                source_cache_sha256=sha(old),maximum_difference_v=abs(y0-previous))
        i=int(np.argmin(abs(e-base[0])));e=e[i:i+n];assert len(e)==n and max(abs(e-base))<.25/fs
        residual=e-base;residual-=np.mean(residual);m=edge_band_power(residual,fs,5e6,492e6)
        row.update(completed=True,band_rms_fs=float(np.sqrt(m['variance'])*1e15),
            rms_relative_to_pnoise=float(np.sqrt(m['variance']/expected)-1),cache_sha256=sha(cache),
            valid_continuation=bool(boundary_ok and row['recovery']['numerically_clean']) if r.get('native_state') else None)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),reference_protocol_sha256=sha(sp),cases=rows,
        effective_band_hz=[g['lower'],g['upper']],pnoise_expected_fs=float(np.sqrt(expected)*1e15),
        physical_dut_modified=False,noise_method_accepted=False,full_pll_acceptance=False,
        findings=['Dynamic tolerance/no-op/isnoisy cases start at100ns but clear the output from1.226281V to0V and produce identical caches. Their clean logs do not validate native recovery or a tolerance fix.',
          'Direct noise fromt0 is clean; normal native activation, static100nV, preinitialized tiny-noise seed and explicit start-time alignment do not resolve the observed recovery problem.'],
        limitations=['Initial parameter tables do not prove dynamic updates; the exact executed parameter schedule is preserved in inputs/launch metadata.',
         'RNG histories differ for direct and native runs; their individual samples must not be compared for equality.',
         'A clean trace does not establish correct noise amplitude, source-bandwidth, step or record-length convergence.',
         'All RMS figures here are diagnostic high-offset values, not fullPLL10kHz acceptance.'])
    (H/'results/retimer_restart_diagnosis_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
