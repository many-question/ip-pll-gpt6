"""Test cold-derived text initialization with delayed noise in one fresh analysis."""
from pathlib import Path
import datetime,hashlib,json,re,shutil
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    j=R/'rt4bankcold01/rt4bank_capture_tt';r=json.loads((j/'result.json').read_text())
    proof=H/'results/capture_rt4bankcold01.json';v=json.loads(proof.read_text());assert r['ok'] and v['functional_capture_screen_passed']
    ic=j/'final.ic';assert sha(ic)==r['state_file']['sha256']
    name='rt4bank_cold64_warm.ic';dst=H/'state_inputs'/name;assert not dst.exists();shutil.copy2(ic,dst)
    body=(j/'inputs'/'rt4bank_capture_tt.scs').read_text()
    body=re.sub(r'^VRST .*$','VRST (reset 0) vsource dc=0',body,flags=re.M)
    body=re.sub(r'^VAP .*$','VAP (apply 0) vsource dc=0',body,flags=re.M)
    body=body.replace('reltol=1e-4','reltol=1e-5')
    body=re.sub(r'^ic .*(?:\n|$)','',body,flags=re.M)
    body=re.sub(r'^tran tran .*$',
        'tran tran stop=300n maxstep=1p strobeperiod=2n strobeoutput=strobeonly method=traponly errpreset=moderate '+
        'readic="'+name+'" skipdc=yes noisefmax=80G noisefmin=1M noiseseed=11 param=isnoisy param_vec=[0 0 1u 1] writefinal="__FINAL_STATE__"',body,flags=re.M)
    case='full_pll_warm_noise_method_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='pllwarmnoisemethod01',case=case,
        source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(j/'result.json'),
        source_capture=proof.name,source_capture_sha256=sha(proof),text_state=name,text_state_sha256=sha(dst),tb_sha256=sha(tb),
        source_time_s=64e-6,local_stop_s=300e-9,noise_enable_s=1e-6,noise_enabled_during_this_trial=False,
        purpose='Validate initialization and steady locked circuit before a fresh single-analysis delayed-noise trial. No native binary restore or static-control replacement.',
        changes='Full physical DUT unchanged. External reset/apply are held at their settled zero values. Original explicit VCO startup perturbation is removed and replaced by measured full-circuit text state. Local reference phase matches64us, an integer1536 reference periods.',
        reference_native_run='pllnoisefloor1p03',reference_native_case='rt4bank_capture_tt',
        full_pll_acceptance=False,random_jitter_measured=False,
        limitations=['writefinal/readic is an incomplete state, not native recovery: hidden model and observer histories can differ. They must settle and be checked.',
          'This is a warm method trial and cannot substitute for the independent-reset acquisition already measured.',
          'The noise-enable event lies after this300ns trial; no RMS noise claim.',
          'Do not adopt if initial physical state, selected code, qualification or later trajectory differs materially from the measured native reference.'],
        primary_method_source='https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/49435/transient-simulation---adding-noise-after-steady-state/1379137')
    pp=H/'results/full_pll_warm_noise_method_protocol.json';assert not pp.exists();pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(run=p['run'],case=case,protocol_sha256=sha(pp)),indent=2))

if __name__=='__main__':main()
