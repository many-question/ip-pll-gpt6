"""Check4MHz PSS/sampleratio246 using analytic sampled RC noise, not PLL performance."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((H/'results/noise_measurement_fixture.json').read_text());assert old['passed']
source=H/'tb/noise_measurement_fixture.scs';base=source.read_text()
base=base.replace('fund=164M harms=383 maxacfreq=1T','fund=4M harms=4095').replace('sampleratio=6','sampleratio=246').replace('maxsideband=383','maxsideband=4095').replace('dec=10','dec=20').replace('method=traponly','method=gear2only tstabmethod=gear2only')
rows=[]
for name,step,ac in [('core',1e-12,None),('fine',.25e-12,1e12)]:
    case='noise_core_cal_'+name;body=base.replace('maxstep=250f','maxstep='+('1p' if name=='core' else '250f'))
    if ac:body=body.replace('harms=4095','harms=4095 maxacfreq=1T')
    dest=H/'tb'/(case+'.scs');assert not dest.exists();dest.write_text(body)
    rows.append(dict(case=case,maxstep_s=step,maxacfreq_hz=ac,tb_sha256=sha(dest)))
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='corecal01',cases=rows,
    source_tb_sha256=sha(source),fund_hz=4e6,sample_ratio=246,sample_frequency_hz=984e6,resistance_ohm=1e3,capacitance_f=20e-15,temperature_k=300.15,
    condition='Same1kohm/20fF linearRC/noiseless984MHz sine. Driven4MHz PSS/246outputrises,gear2only,10kHz–492MHz explicit sampledPSD/slope2 integral.',
    limits=dict(period_relative=1e-8,endpoint_v=1e-3,rms_relative_to_analytic=.005,core_to_fine_rms_relative=.005,core_to_fine_psd_db=.1,clipped_vs_auto_jee_relative=.015),
    launch_gate='Finite two-case calibration after both rt4program01 cases complete; reuse one-thread shortslot, no overlap beyond18threads.',
    analytic='Stationary RC covariance sigma2*rho^abs(k),sigma2=kT/C,rho=exp[-1/(fsRC)]. One-sided sampledSv=2*kT/(Cfs)*(1-rho2)/(1-2rho*cos(2pif/fs)+rho2). Divide by analytic sine output zero-crossing slope squared.',
    limitations=['Linear thermal-noise normalization only; not realPLL RMS, MOS/readpss accuracy or nonidentical-edge covariance.','This does not resolve shifted1/f poles or validate omitted fullPLLcontrolnoise.','Core-to-fine changes grid andmaxacfreq together, so a difference diagnoses combinednumericalaccuracy,notuniquecausality.'],
    evidence_sources=[dict(path='research/spectre_help/pnoise.txt',sha256=sha(ROOT/'research/spectre_help/pnoise.txt'),supports='sampleratio is samplefrequency/PSSfund; parameter semantics only.'),
        dict(url='https://community.cadence.com/cadence_technology_forums/f/rf-design/49427/sampled-pnoise-on-multi-phase-switched-cap-circuit/1379074',accessed='2026-10-04',supports='Cadence staff identifies sampled(jitter) for21.1; linked support-note details require access and were not read.'),
        dict(url='https://support1.cadence.com/public/docs/content/20483291.html',accessed='2026-10-04',status='403; no content used')],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_noise_calibration_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(' '.join(x['case'] for x in rows))
