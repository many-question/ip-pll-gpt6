"""Prepare a finite analytic RC control for enabling noise after native recovery."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/transient_noise_recovery_protocol.json';assert not pp.exists()
    template='''simulator lang=spectre
global 0
simulatorOptions options temp=27 reltol=1e-6 vabstol=1e-9 iabstol=1e-15
VD (drive 0) vsource dc=1.2
R (drive out) resistor r=1k
C (out 0) capacitor c=1p
save out
saveOptions options save=selected
tran tran stop=STOP maxstep=10p strobeperiod=100p strobeoutput=strobeonly method=traponly errpreset=conservative noisefmax=NOISE noisefmin=1M noiseseed=11 savefile="__NATIVE_SAVE__" savetime=[SAVE] writefinal="__FINAL_STATE__"
'''
    cases=[]
    for name,stop,noise in [('noise_recover_rc_seed', '2u','0'),('noise_recover_rc_direct','10u','10G')]:
        tb=H/'tb'/(name+'.scs');assert not tb.exists()
        tb.write_text(template.replace('STOP',stop).replace('NOISE',noise).replace('SAVE]',stop+']'),encoding='utf-8',newline='\n')
        cases.append(dict(case=name,tb_sha256=sha(tb),run='noiserecovercontrol01' if name.endswith('_seed') else 'noiserecoverdirect01'))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
        condition='Analytic one-pole resistor/capacitor; R=1kOhm,C=1pF,T=300.15K,1.2V noiseless drive. No PDK/MOS or PLL.',
        resistance_ohm=1000.,capacitance_f=1e-12,temperature_k=300.15,
        measurement_start_s=2.1e-6,measurement_stop_s=10e-6,saved_time_s=2e-6,
        recovery_cases=[dict(run='noiserecoveroff01',noisefmax=0.,noisefmin=1e6,noiseseed=11),
            dict(run='noiserecoveron11',noisefmax=1e10,noisefmin=1e6,noiseseed=11),
            dict(run='noiserecoveron29',noisefmax=1e10,noisefmin=1e6,noiseseed=29),
            dict(run='noiserecover20g',noisefmax=2e10,noisefmin=1e6,noiseseed=11)],
        gates=dict(variance_relative_error=.10,mean_error_sigma=5.,noiseless_rms_v=1e-9,
                   direct_vs_recovered_variance_relative_difference=.10,bandwidth_variance_relative_difference=.10),
        observation='Variance of uniform100ps samples after2.1us; DC mean removed. Expected one-sided integral of4kTR/(1+(2*pi*f*RC)^2) up to source bandwidth.',
        fresh_pss=False,main_dut_modified=False,full_pll_acceptance=False,
        launch_scope='One short diagnostic slot, serial1thread cases,each300s guard; source then four native branches and one direct-noise case.',
        limitations=['This tests source-noise activation and deterministic-state recovery only; it does not validate nonlinear PLL noise or coloured-noise folding.',
            'Noisefmin is a device-noise spectrum corner, not a highpass measurement cutoff. Resistor source is white in this control.',
            'Sub-10kHz and10kHz PLL observations need a much longer actual record; this short control cannot validate the full requested jitter band.',
            'Native recovery is within transient analysis; no transfer to PSS and no readpss reuse.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(pp)

if __name__=='__main__':main()
