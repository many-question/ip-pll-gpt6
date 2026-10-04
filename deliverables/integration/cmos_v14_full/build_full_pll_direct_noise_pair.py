"""Prepare matched full-transistor noise-off/on traces after tolerance diagnosis."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
from transient_diagnostics import recovery
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    j=R/'pllabsoluteiab01/full_pll_absolute_iab_tt';r=json.loads((j/'result.json').read_text())
    assert r['ok'] and recovery((j/'spectre.out').read_text())['numerically_clean']
    source=H/'tb/full_pll_absolute_iab_tt.scs';body=source.read_text().replace('stop=5n','stop=2.2u')
    body=body.replace('strobeoutput=all','strobeoutput=strobeonly skipstop=1u').replace(' diagnose=yes','')
    # Preserve every original current probe to keep the physical node equations.
    saves=['out','ref','qualified','range_error','cfg_ready','frequency_good','phase_good','amp_good',
        'XP.ctrl','XP.vp','XP.vn','XP.refb','XP.XC.phase_held','XP.XC.acquired','XP.en',
        'VDD:p','XP.VVCO:p','XP.VRX:p','XP.VRT:p']
    body=re.sub(r'^save .*\n','',body,flags=re.M)+'save '+' '.join(saves)+'\n'
    cases=[]
    for label,value in [('off',0),('on',1)]:
        case='full_pll_direct_noise_'+label+'_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        tb.write_text(body.replace('param_vec=[0 0 3u 1]',f'param_vec=[0 0 1u {value}]'))
        cases.append(dict(run='pllnoisedirect'+label+'01',case=case,noise_enabled=value==1,tb_sha256=sha(tb)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,source_result=(j/'result.json').relative_to(ROOT).as_posix(),
        source_result_sha256=sha(j/'result.json'),source_tb_sha256=sha(source),text_state='rt4bank_cold64_no_observer.ic',
        text_state_sha256=sha(H/'state_inputs/rt4bank_cold64_no_observer.ic'),
        condition='Actual full RT4/newbank PLL with transistor FLL/control/watchdog/bias,TT27/1.2V/24MHzref/K41/M4/10fF/Q5RLC/CF10; ideal external reference and supply.',
        output_hz=984e6,ref_hz=24e6,stop_s=2.2e-6,noise_start_s=1e-6,measurement_start_s=1.1e-6,edge_count=1024,band_hz=[5e6,492e6],
        maxstep_s=.5e-12,reltol=1e-6,vabstol=1e-9,iabstol=1e-12,noisefmax_hz=160e9,noisefmin_hz=1e6,seed=11,
        observations=saves,physical_dut_modified=False,full_pll_acceptance=False,
        limitations=['This is an initial high-offset complete-circuit diagnostic, not the10kHz/full-band acceptance.',
          '5ns absolute-current-tolerance comparison validates only short numerical behavior. Require clean whole traces, intact physical initial state, common quiet prefix and stationary noiseless loop.',
          'Measurement inputs are ideal; actual transistor noise in every PLL device and RLC resistance is enabled together in the on case.',
          'No functional control is clamped. The two measurement-only VA modules were removed and an ideal0V supply probe substituted.',
          'No source-amplitude scaling, fitted trend removal or arbitrary spur notches. Paired deterministic edge template removes the measured repeatable component.',
          'Further timestep, current-tolerance, bandwidth, seed and record-length comparisons remain mandatory even if this pair finishes cleanly.'])
    for c in cases:
        tb=H/'tb'/(c['case']+'.scs');tb.write_text(tb.read_text().replace('noisefmax=80G','noisefmax=160G'));c['tb_sha256']=sha(tb)
    pp=H/'results/full_pll_direct_noise_pair_protocol.json';assert not pp.exists();pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(cases=cases,protocol_sha256=sha(pp)),indent=2))

if __name__=='__main__':main()
