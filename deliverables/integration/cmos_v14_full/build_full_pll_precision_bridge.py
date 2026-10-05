"""Preserve the physical PLL while preparing a fine-precision operating point."""
from pathlib import Path
import datetime, hashlib, json, re
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def save(path,body):
    assert not path.exists(),path
    path.write_text(body,encoding='utf-8',newline='\n')

def main():
    old=H/'results/full_pll_direct_noise_pair_protocol.json'
    p=json.loads(old.read_text())
    source=R/'repaircoldstrict01/repair_capture_strict_tt'
    evidence=H/'results/capture_repaircoldstrict01.json'
    v=json.loads(evidence.read_text()); assert v['stationarity']['passed']
    r=json.loads((source/'result.json').read_text()); assert r['ok'] and r['remote_inputs_match']
    # Match all physical dependencies to the completed independent-reset run.
    available={p.name:p for p in (H.parents[1]/'blocks').glob('*/*.scs')}
    physical={k:s for k,s in r['inputs_sha256'].items() if k.endswith('.scs') and not k.startswith('repair_capture')}
    assert all(sha(available[k])==s for k,s in physical.items())
    ic=source/'final.ic'; removed={};kept=[]
    excluded={'energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles','VAP:p','VRST:p'}
    for line in ic.read_text().splitlines():
        if not line.strip() or line.startswith('#'):kept.append(line);continue
        name=line.split()[0]
        if name in excluded or name.startswith(('XE:','XOBS:')):removed[name]=line
        else:kept.append(line)
    currents={s.split()[0]:float(s.split()[1]) for s in kept if s.strip() and not s.startswith('#')}
    kept.append('VMEAS:p\t'+str(currents['VDD:p'])+'\t#A')
    state=H/'state_inputs/main_strict64_no_observer.ic'
    save(state,'\n'.join(kept)+'\n')
    original=(H/'tb/full_pll_direct_noise_off_tt.scs').read_text()
    body=original.replace('pll_capture_rt4bank_v14','pll_capture_v14').replace('rt4bank_cold64_no_observer.ic',state.name)
    # Add only observations of the actual reset and held sampler state.
    body=body.replace('save out ref ','save XP.restart XP.hp XP.hn XP.vc1 out ref ')
    cases=[]
    for label,value in [('off',0),('on',1)]:
        name='full_pll_main_strict_'+label+'_tt'; tb=H/'tb'/(name+'.scs')
        save(tb,body.replace('param_vec=[0 0 1u 0]',f'param_vec=[0 0 1u {value}]'))
        cases.append(dict(run='pllmainstrict'+label+'01',case=name,noise_enabled=bool(value),tb_sha256=sha(tb)))
    p.update(scope='Original complete V14, measured1ps cold-acquisition state; matched fresh noise pair.',
        time=datetime.datetime.now().astimezone().isoformat(),cases=cases,text_state=state.name,text_state_sha256=sha(state),
        condition='Original complete V14, all actual transistor FLL/control/watchdog/bias,TT27/1.2V/24MHz/K41/M4/10fF/Q5RLC/CF10; original output chain. Ideal external reference and supply.',
        source_result=(source/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(source/'result.json'),
        source_capture=evidence.name,source_capture_sha256=sha(evidence),source_ic_sha256=sha(ic),
        removed_nonphysical_ic_entries=removed,physical_dependency_hashes=physical,
        deployment_rule='Run quiet first. Noise may launch only after the quiet trace passes numerical, initialization, logic and stationarity checks. Never mix this result with RT4 candidate.',
        observations=p['observations']+['XP.restart','XP.hp','XP.hn','XP.vc1'])
    save(H/'results/full_pll_main_strict_pair_protocol.json',json.dumps(p,indent=2)+'\n')
    # Small real-MOS test of the installed simulator's dynamic precision API.
    probe='precision_schedule_probe_tt'
    head=original.split('include "pll_capture_rt4bank_v14.scs"')[0]
    smoke=head+'''include "cells.scs"
simulatorOptions options temp=27 reltol=1e-4 vabstol=1e-6 iabstol=1e-12
VDD (vdd 0) vsource dc=1.2
VI (inp 0) vsource type=pulse val0=0 val1=1.2 period=1n width=480p rise=20p fall=20p delay=100p
XI (inp out vdd 0) pll_inv
CL (out 0) capacitor c=10f
precision_steps paramset {
time maxstep reltol vabstol iabstol isnoisy
0 4p 1e-4 1e-6 1e-12 0
2n 2p 1e-5 1e-7 1e-12 0
4n .5p 1e-6 1e-9 1e-12 0
6n .5p 1e-6 1e-9 1e-12 1
}
tran tran stop=8n maxstep=4p method=traponly errpreset=moderate noisefmax=160G noisefmin=1M noiseseed=11 paramset=precision_steps
saveOptions options save=selected
save inp out VDD:p
'''
    save(H/'tb'/(probe+'.scs'),smoke)
    # Numerical initialization bridge only: no physical parameter/state/threshold changes.
    steps=[dict(time_s=0.,maxstep_s=4e-12,reltol=1e-4,vabstol=1e-6,iabstol=1e-12,isnoisy=0)]
    for n in range(1,15):
        steps.append(dict(time_s=n*1e-6,maxstep_s=(4-.25*n)*1e-12,reltol=1e-4,vabstol=1e-6,iabstol=1e-12,isnoisy=0))
    steps.extend([dict(time_s=15e-6,maxstep_s=.5e-12,reltol=1e-5,vabstol=1e-7,iabstol=1e-12,isnoisy=0),
                  dict(time_s=16e-6,maxstep_s=.5e-12,reltol=1e-6,vabstol=1e-9,iabstol=1e-12,isnoisy=0)])
    schedule='precision_steps paramset {\ntime maxstep reltol vabstol iabstol isnoisy\n'
    schedule+='\n'.join(' '.join(format(s[k],'.12g') for k in ['time_s','maxstep_s','reltol','vabstol','iabstol','isnoisy']) for s in steps)+'\n}\n'
    ramp=original.replace('reltol=1e-6 vabstol=1e-9','reltol=1e-4 vabstol=1e-6')
    ramp=ramp.replace('tran tran stop=2.2u maxstep=.5p',schedule+'tran tran stop=20u maxstep=4p')
    ramp=ramp.replace(' skipstop=1u','').replace('param=isnoisy param_vec=[0 0 1u 0]','paramset=precision_steps')
    ramp=ramp.replace('save out ref ','save XP.restart XP.hp XP.hn XP.vc1 out ref ')
    rampcase='full_pll_rt4_precision_ramp_tt';tb=H/'tb'/(rampcase+'.scs');save(tb,ramp)
    protocol=dict(scope='Allow the unchanged physical RT4 PLL to adapt while numerical timestep is reduced gradually.',
        time=datetime.datetime.now().astimezone().isoformat(),run='pllprecisionramp01',case=rampcase,tb_sha256=sha(tb),
        prerequisite_probe_run='pllprecisionprobe01',prerequisite_probe_case=probe,probe_tb_sha256=sha(H/'tb'/(probe+'.scs')),
        source_pair_protocol_sha256=sha(old),text_state='rt4bank_cold64_no_observer.ic',
        text_state_sha256=sha(H/'state_inputs/rt4bank_cold64_no_observer.ic'),schedule=steps,stop_s=20e-6,
        physical_dut_modified=False,noise_enabled=False,full_pll_acceptance=False,
        purpose='Diagnosis of abrupt numerical-precision frequency shift versus loss of physical lock. No modified controls, forced codes, widened phase window or reset suppression.',
        final_precision='0.5ps/reltol1e-6/vabstol1nV/iabstol1pA, maintained16–20us.',
        limitations=['Warm initialization only; not an independent reset/cold-acquisition result.',
          'Scheduled precision is never used to measure jitter. A subsequent separate constant-precision settling/noise check is required.',
          'Final waveform is sparse; only logic and held-node behavior can be accepted from this run. Dense RF/output stationarity must be checked subsequently.',
          'Stop on actual reentry to acquisition or numerical recovery; do not force qualification.'])
    save(H/'results/full_pll_precision_ramp_protocol.json',json.dumps(protocol,indent=2)+'\n')
    print(json.dumps(dict(main_cases=cases,ramp=protocol['run'],probe='pllprecisionprobe01'),indent=2))

if __name__=='__main__':main()
