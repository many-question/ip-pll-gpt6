"""Same MOS buffer, fresh PSS with one versus six physical clock periods.

This calibrates sampled-noise handling in a cyclostationary MOS circuit,
including finite neighbours of the artificial 164/328/492 MHz harmonics.
It is neither a divider noise result nor a full PLL measurement.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
PDK='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    offsets=[1e4,1e6,1e8,163999999,164000001,327999999,328000001,491990000,491999999,492000000]
    body=f'''simulator lang=spectre
global 0
include "{PDK}" section=tt
include "{PDK}" section=stat_noise
simulator lang=spectre insensitive=no
include "cells.scs"
simulatorOptions options temp=27 reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VDD (vdd 0) vsource dc=1.2
VIN (in 0) vsource type=pulse val0=0 val1=1.2 period={1/984e6:.17g} width={.5/984e6-10e-12:.17g} rise=10p fall=10p
// Same two final CMOS stages as RT4; ideal input isolates the measurement.
X0 (in ob vdd 0) pll_inv wn=12u wp=2u
X1 (ob out vdd 0) pll_inv wn=3.2u wp=12u
CL (out 0) capacitor c=10f
save in ob out VDD:p
saveOptions options save=selected
'''
    cases=[]
    for ratio,harms in [(1,128),(6,768)]:
        case=f'mos_period_ratio{ratio}_tt'; dest=H/'tb'/(case+'.scs');assert not dest.exists()
        # Both TD and small-signal cutoffs match in absolute Hz. Harmonic count
        # scales with superperiod; use identical maxacfreq/full-spectrum settings.
        tb=body+f'''pss pss fund={984e6/ratio:.17g} harms={harms} tstab=30n maxstep=0.5p maxacfreq=504G method=traponly errpreset=conservative maxperiods=30 saveinit=no writefinal="__FINAL_STATE__" writepss="__PERIODIC_STATE__"
pn pnoise values=[{' '.join(f'{f:.17g}' for f in offsets)}] pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio={ratio} maxsideband={harms}
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
'''
        dest.write_text(tb,encoding='utf-8',newline='\n')
        cases.append(dict(case=case,run='mosperiodax01',ratio=ratio,fund_hz=984e6/ratio,harms=harms,tb_sha256=sha(dest)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
        condition='TT27/1.2V/984MHz ideal10ps-edge input/two RT4-sized inverters/10fF. FreshPSS each, .5ps/trap/reltol1e-5/maxacfreq504GHz.',
        required_mode='ax +mt=1 -preset_override (fullspectrum requires APS family)',
        offsets_hz=offsets,comparison_limits=dict(max_timing_psd_delta_db=.1,max_relative_slew_difference=.005,max_waveform_difference_v=1e-3),
        limitations=['Same physical 984MHz buffer repeated over a six-cycle superperiod; it does not prove equivalence for genuinely different edge positions in the divider.',
            'Sparse finite points are not a jitter integral and do not supply a physical 1/f low-frequency cutoff.',
            'A failure must be investigated as numerical/measurement evidence before it is attributed to MOS geometry.'],
        full_pll_acceptance=False,main_dut_modified=False)
    path=H/'results/mos_period_noise_protocol.json';assert not path.exists();path.write_text(json.dumps(p,indent=2)+'\n')
    print([x['case'] for x in cases])

if __name__=='__main__':main()
