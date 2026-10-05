"""Short complete-MOS noise activation diagnosis; no RMS acceptance claim."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    pp=H/'results/full_pll_main_strict_pair_protocol.json';p=json.loads(pp.read_text())
    src=H/'tb/full_pll_main_strict_on_tt.scs';s=src.read_text()
    s=s.replace('stop=2.2u','stop=200n').replace('skipstop=1u','skipstop=50n').replace('param_vec=[0 0 1u 1]','param_vec=[0 0 50n 1]')
    case='full_pll_noise_activation_probe_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(s)
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='pllnoiseactivation01',case=case,
        condition=p['condition'],parent_protocol_sha256=sha(pp),tb_sha256=sha(tb),text_state=p['text_state'],text_state_sha256=p['text_state_sha256'],
        noise_start_s=50e-9,stop_s=200e-9,maxstep_s=.5e-12,reltol=1e-6,vabstol=1e-9,iabstol=1e-12,
        noisefmax_hz=160e9,noisefmin_hz=1e6,seed=11,
        purpose='Verify that fresh delayed activation runs actual native device noise through the whole original transistor PLL without Newton recovery, skipped breakpoints, state clearing or loss of lock.',
        full_pll_acceptance=False,integrated_jitter_fs=None,
        limitations=['Only150ns of actual noise; no low-offset or RMS result.',
                     'Analog state is still settling from a measured1ps cold result. Do not claim stationary noise.',
                     'Independent full quiet/on baseline, tolerance, bandwidth and statistical convergence remain necessary.'])
    dst=H/'results/full_pll_noise_activation_probe_protocol.json';assert not dst.exists();dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
