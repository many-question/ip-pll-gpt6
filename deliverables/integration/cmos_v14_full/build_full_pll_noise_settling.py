"""Prepare strict full-transistor PLL settling before a delayed-noise measurement."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/full_pll_warm_noise_method_validation.json';v=json.loads(proof.read_text())
    assert v['initialization_screen_passed']
    source=H/'tb/full_pll_warm_noise_method_tt.scs';body=source.read_text()
    body=body.replace('reltol=1e-5 vabstol=1e-6 iabstol=1e-12','reltol=1e-6 vabstol=1e-9 iabstol=1e-15')
    body=body.replace('stop=300n maxstep=1p','stop=2u maxstep=.5p').replace('param_vec=[0 0 1u 1]','param_vec=[0 0 3u 1]')
    case='full_pll_noise_settling_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='pllnoisesettle01',case=case,
        source_tb_sha256=sha(source),tb_sha256=sha(tb),initialization_validation=proof.name,initialization_validation_sha256=sha(proof),
        text_state='rt4bank_cold64_warm.ic',text_state_sha256=sha(H/'state_inputs/rt4bank_cold64_warm.ic'),
        condition='Actual full RT4/newbank PLL,TT27/1.2V/K41/M4/10fF/Q5/CF10; ideal external reference and supply.',
        stop_s=2e-6,noise_enabled=False,noise_enable_s=3e-6,maxstep_s=.5e-12,reltol=1e-6,vabstol=1e-9,iabstol=1e-15,
        measurement_start_s=1e-6,source_time_s=64e-6,
        checks=dict(phase_pp_rad=.02,phase_drift_rad_per_us=.01,rf_cycles_error=.001,out_cycles_error=.001),
        full_pll_acceptance=False,physical_dut_modified=False,
        limitations=['Settling/lock screen only; noise remains off throughout this2us analysis.',
         'Fresh text initialization validated against cold/native physical states but does not preserve complete hidden histories.',
         'Tighter tolerances can change the numerical operating point; do not infer a device-noise RMS from that motion.',
         'The2ns saved grid only observes held state/phase values; it cannot resolve GHz edges for jitter.'])
    pp=H/'results/full_pll_noise_settling_protocol.json';assert not pp.exists();pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(run=p['run'],case=case,protocol_sha256=sha(pp)),indent=2))

if __name__=='__main__':main()
