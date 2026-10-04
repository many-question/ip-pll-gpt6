"""Screen one reference-buffer sizing candidate with real-device edge noise.

Keep the last driver unchanged; enlarge upstream stages from1/4/16 to8/16/32um.
The standalone2pF load is an explicit approximation, not the frontend load.
"""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/frontend_noise_r2_all_validation.json';v=json.loads(proof.read_text());assert v['noise_valid']
    source=H.parents[1]/'blocks/transistor_v1/cells.scs'
    old=re.search(r'^subckt tx_reference_buffer .*?^ends tx_reference_buffer$',source.read_text(),re.M|re.S)[0]
    name='reference_buffer_taper2_v14';body=old.replace('tx_reference_buffer',name)
    changes={'wn=1u wp=2.5u':'wn=8u wp=20u','wn=4u wp=10u':'wn=16u wp=40u','wn=16u wp=40u':'wn=32u wp=80u'}
    # Stage-specific substitution avoids cascading an earlier replacement.
    lines=body.splitlines()
    for i,(before,after) in enumerate(changes.items()):
        at=next(k for k,line in enumerate(lines) if line.startswith('X'+str(i)+' '))
        assert before in lines[at];lines[at]=lines[at].replace(before,after)
    body='simulator lang=spectre\n// Noise candidate; original reference-buffer cell remains unchanged.\n'+'\n'.join(lines)+'\n'
    block=B/(name+'.scs');pp=H/'results/reference_buffer_noise_protocol.json'
    cases=[dict(variant=a,case='reference_buffer_'+a+'_tt',subckt=b) for a,b in [('baseline','tx_reference_buffer'),('taper2',name)]]
    assert not any(p.exists() for p in [block,pp,*[H/'tb'/(c['case']+'.scs') for c in cases]])
    block.write_text(body,encoding='utf-8',newline='\n')
    for c in cases:
        extra='include "'+block.name+'"\n' if c['variant']=='taper2' else ''
        tb=f'''simulator lang=spectre
global 0
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section=tt
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section=stat_noise
simulator lang=spectre insensitive=no
include "cells.scs"
{extra}simulatorOptions options temp=27 reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VDD (vdd 0) vsource dc=1.2
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n
XR (ref out vdd 0) {c['subckt']}
CL (out 0) capacitor c=2p
save ref out XR.a XR.b XR.c VDD:p VR:p
saveOptions options save=selected
pss pss fund=24M harms=1023 tstab=100n maxstep=1p maxacfreq=96G method=gear2only tstabmethod=gear2only errpreset=conservative maxperiods=20 saveinit=no writefinal="__FINAL_STATE__" writepss="__PERIODIC_STATE__"
pn pnoise start=10k stop=12M dec=20 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=1 maxsideband=1023
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
'''
        path=H/'tb'/(c['case']+'.scs');path.write_text(tb,encoding='utf-8',newline='\n')
        c.update(run='refbuffernoise01',tb_sha256=sha(path),dependencies_sha256={source.name:sha(source),**({block.name:sha(block)} if extra else {})})
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
           source_noise_validation=proof.name,source_noise_validation_sha256=sha(proof),
           condition='TT27/1.2V/24MHz ideal10psreference/2pF explicitoutputload/actualMOS, freshPSS; standalone referencebuffer only.',
           original_nm_widths_um=[1,4,16,64],candidate_nm_widths_um=[8,16,32,64],pm_to_nm_width_ratio=2.5,channel_length_nm=180,
           integration_band_hz=[1e4,12e6],numerical_settings=dict(maxstep_ps=1,maxacfreq_ghz=96,harms=1023,maxsideband=1023),
           main_dut_modified=False,full_pll_acceptance=False,launch_scope='Two serial one-thread small-circuit cases in one short diagnostic slot;3600s percase guard.',
           limitations=['The2pF lumpedload approximates previous1.9pFcontrol+60fFexplicitload and small gate loads; no nonlinear RF-sampler loading.',
                        'Input source is ideal; increased first-stage input capacitance is not loaded onto a finite source impedance.',
                        'Referenceedge jitter10kHz-12MHz is a module diagnostic, not fullPLL10kHz-fOUT/2 acceptance.',
                        'Candidate requires numerical convergence, PVT, rebalance and noisyfrontend verification before adoption.',
                        'Sizing upstream stages changes delay, transitions and dynamiccurrent; it is not a pure flicker-coefficient experiment.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(p,indent=2))

if __name__=='__main__':main()
