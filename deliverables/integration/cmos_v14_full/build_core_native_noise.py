"""Use the measured observer-free periodic candidate for one fresh PSS/noise trial."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
vp=H/'results/core_native_period_validation.json';v=json.loads(vp.read_text())
assert v['ready_for_pss_review'] and v['dense_periods_passed'] and v['all_state_endpoint_screen_passed']
p=json.loads((H/'results/core_plain_warm_protocol.json').read_text())
j=(ROOT/v['source_result']).parent;r=json.loads((j/'result.json').read_text())
assert sha(j/'result.json')==v['source_sha256'] and r['ok'] and r['remote_inputs_match']
assert sha(j/'final.ic')==r['local_outputs_sha256']['final.ic']
states={}
for line in (j/'final.ic').read_text().splitlines():
    z=line.split()
    if z and z[0] in p['physical_state_units']:
        assert ('A' if re.search(r'#unit\s+A\s*$',line) else 'V')==p['physical_state_units'][z[0]]
        states[z[0]]=line
assert len(states)==612
case='core_native_noise_tt';seed=H/'state_inputs'/(case+'.ic');assert not seed.exists()
seed.write_text('# Exact612 physical states at3.5us from native observer-free continuation; no correction.\n'+'\n'.join(states[k] for k in p['physical_state_units'])+'\n')
body=(j/'inputs'/(j.name+'.scs')).read_text()
assert 'XOBS' not in body and 'strobeperiod' not in body and body.count('tran tran ')==1
analysis=f'''pss pss fund=4M harms=4095 tstart=3.5u tstab=250n skipdc=yes readic="{seed.name}" maxstep=1p method=gear2only tstabmethod=gear2only errpreset=conservative maxperiods=6 saveinit=yes writefinal="__FINAL_STATE__" writepss="__PERIODIC_STATE__"
pn pnoise values=[1M 10M 99.99M] pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=246 maxsideband=4095
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]'''
body=re.sub(r'^tran tran .*$',analysis,body,flags=re.M)
assert ' recover=' not in body and 'skipcount=' not in body
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
# The project source tree still supplies exactly the physical files used in
# the native run. A new PSS trial must not silently acquire unrelated edits.
available={}
for folder in ['transistor_v1','transistor_v2','transistor_v3','vco_v4','interface_v5','closure_v6','accuracy_v7','output_v8','output_v9','noise_v10','jitter_v11','cmos_v12','cmos_v13','cmos_v14','cmos_v14_full']:
    for f in (H.parents[1]/'blocks'/folder).glob('*'):
        if f.suffix in ['.scs','.va']:available[f.name]=f
physical={k:x for k,x in r['inputs_sha256'].items() if k.endswith(('.scs','.va')) and k!=j.name+'.scs'}
assert all(sha(available[k])==x for k,x in physical.items())
out=dict(scope=__doc__,run='corenativenoise01',case=case,time=datetime.datetime.now().astimezone().isoformat(),
    source_validation_sha256=sha(vp),source_result=v['source_result'],source_result_sha256=v['source_sha256'],
    source_final_ic_sha256=sha(j/'final.ic'),seed_sha256=sha(seed),tb_sha256=sha(tb),physical_dependencies_sha256=physical,
    physical_state_units=p['physical_state_units'],expected_rising_edges_per_period=p['expected_rising_edges_per_period'],
    condition='ActualLC/originalRT/CF10/newbank/coarse23/DAC38/M4/TT27/1.2V/Q5/10fF/refload1.9pF; ideal static acquired/FLL controls. No eventobserver/forcedstrobe.',
    timing=dict(initial_state_absolute_time_s=3.5e-6,tstart_s=3.5e-6,tstab_s=250e-9,fund_hz=4e6,maxstep_s=1e-12,maxperiods=6,method='gear2only'),
    noise_offsets_hz=[1e6,10e6,99.99e6],
    rationale='Native observer-free500ns evolution passes all original1mV/10ppm/11branch screens. PriorPSS was seeded before this mesh-consistent evolution; this trial uses its measuredactualendpoint. Noise analyses run only if Spectre reachesPSS.',
    limitations=['All612exported states are real, but textreadic cannotretainhiddencharge/history; PSS must solve and validateitsownperiod.',
        'Gear2 may cause numerical damping; successful PSS stillneedsindependentprecisionchecks.',
        'Three noise points are not an integrated jitter result or an all246-edge covariance qualification.',
        'Static slowcontrols omit completeFLL/watchdog dynamics; this is actualperiodiccore evidence,notfullPLLsignoff.',
        'No MOS readpss reuse: earlier fresh/reused noise discrepancy remains unresolved.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_native_noise_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(case)
