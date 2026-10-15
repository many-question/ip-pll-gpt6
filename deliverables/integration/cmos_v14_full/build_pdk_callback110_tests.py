"""Three small paired TT module experiments; no full PLL is dispatched."""
from pathlib import Path
import json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[4];H=ROOT/'share/deliverables/integration/cmos_v14_full'
D=json.loads((H/'results/pdk_callback110_parameters.json').read_text());E=D['module_entrypoints']
MODEL='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
def entry(path,v):return E['XPLL.'+path][v]
def build():
    cases=[]
    for module in ('cpref','rfchain','vco'):
        for v in ('before','after'):
            name='pdkcb110_'+module+'_'+v
            s='simulator lang=spectre\nglobal 0\n'
            for sec in ('tt','stat_noise','tt_bbmvar'):
                s+='include "'+MODEL+'" section='+sec+'\nsimulator lang=spectre insensitive=no\n'
            s+='include "rt4_callback110_'+v+'.scs"\n'
            s+='simulatorOptions options reltol=1e-3 vabstol=1e-6 iabstol=1e-12 temp=27\nVDD (vdd 0) vsource dc=1.2\n'
            if module=='cpref':
                stop=300e-9;strobe=5e-12
                s+='''VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n
VP (pulse 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=2n rise=10p fall=10p delay=20n
VHP (hp 0) vsource type=pwl wave=[0 .61 150n .61 150.01n .59 300n .59]
VHN (hn 0) vsource dc=.6
VOUT (cpout 0) vsource dc=.6
CR (refb 0) capacitor c=60f
'''
                s+=f'XREF (ref refb vdd 0) {entry("XREF",v)}\nXCP (hp hn pulse vdd cpout vdd 0) {entry("XCP",v)}\n'
                s+='save ref refb pulse hp hn cpout XCP.nb XCP.ng XCP.tail VDD:p VOUT:p\n'
                scope='Reference buffer 24MHz/60fF and CP +/-10mV input, 2ns pulse, output clamped .6V'
            elif module=='rfchain':
                stop=120e-9;strobe=5e-12
                s+='VRF (vp 0) vsource type=sine dc=1.2 ampl=.4 freq=3.936G\n'
                s+='VDRESET (div_reset 0) vsource type=pwl wave=[0 1.2 20n 1.2 20.01n 0]\n'
                s+=f'XRX (vp clk vdd 0) {entry("XRX",v)}\nXD (clk div_reset vdd 0 0 0 0 0 q1 data acqclk vdd 0) {entry("XD",v)}\nXR (data clk out vdd 0) {entry("XR",v)}\n'
                s+='CL (out 0) capacitor c=10f\nsave vp clk q1 data out acqclk VDD:p\n'
                scope='3.936GHz sine driven RF receiver, hardware divide4 and RT4; 10fF load'
            else:
                stop=400e-9;strobe=5e-12
                s+='VC (ctrl 0) vsource dc=.48\n'
                for bit in range(8):s+=f'VB{bit} (b{bit} 0) vsource dc={1.2 if (20>>bit)&1 else 0}\n'
                s+=f'XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vdd 0) {entry("XV",v)}\n'
                s+=f'XBM (vdd 0 vmid) {entry("XBM",v)}\n'
                s+='''CCP (vp sp) capacitor c=120f
CCN (vn sn) capacitor c=120f
RBP (sp vmid) resistor r=10k
RBN (sn vmid) resistor r=10k
VR (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n
CR (refb 0) capacitor c=60f
VPULSE (pulse 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=2n rise=10p fall=10p delay=20n
VO (cpout 0) vsource dc=.6
VDRESET (div_reset 0) vsource type=pwl wave=[0 1.2 20n 1.2 20.01n 0]
CL (out 0) capacitor c=10f
'''
                s+=f'XREF (ref refb vdd 0) {entry("XREF",v)}\nXS (refb sp sn hp hn vdd 0) {entry("XS",v)}\nXCP (hp hn pulse vdd cpout vdd 0) {entry("XCP",v)}\n'
                s+=f'XRX (vp clk vdd 0) {entry("XRX",v)}\nXD (clk div_reset vdd 0 0 0 0 0 q1 data acqclk vdd 0) {entry("XD",v)}\nXR (data clk out vdd 0) {entry("XR",v)}\nXDET (vp hp hn amp_good phase_good vdd 0) {entry("XDET",v)}\n'
                s+='ic vp=1.20001 vn=1.2 XV.XL.nfilt=.728\nsave vp vn ctrl clk q1 data out sp sn hp hn ref refb XV.XL.nb XV.XL.nfilt XV.XL.tail VDD:p amp_good phase_good\n'
                scope='Local loaded VCO coarse20/control.48V, original free 1Mohm/10pF bias network; warm .728V initial bias, 400ns is not asymptotic steady state or full PLL lock'
            s+=f'tran tran stop={stop:.12g} start=0 strobeperiod={strobe:.12g} maxstep=8p method=traponly errpreset=moderate writefinal="__FINAL_STATE__"\nsaveOptions options save=selected\n'
            p=H/'tb'/f'{name}.scs';assert not p.exists();p.write_text(s)
            cases.append(dict(run='pdkcb110ssd01',case=name,module=module,version=v,kind='diagnostic',stop_s=stop,strobe_s=strobe,expected_points=round(stop/strobe)+1,requested_threads=2,scope=scope,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    p=dict(time=datetime.datetime.now().astimezone().isoformat(),trigger='User pdk-callback request; current full capture left untouched',mode='ax',maxstep_s=8e-12,reltol=1e-3,method='traponly',noise=False,corner='TT',temp_C=27,supply_V=1.2,cases=cases,resources='One sequential short worker, 2 requested threads alongside original 4-thread recenter109; maximum18/4long+1short',source_parameters='results/pdk_callback110_parameters.json',do_not_modify_or_restart='rt4center109ssd01 / rt4r48_recenter109_k41_tt',completion='Explicit exit0/zero errors/PSF END, physical finite full records and remote input/raw/log/final.ic hashes; normal solver completion is separate from functionality',evidence_boundary='Independent callback candidate; no full PLL or jitter/PVT claim')
    (H/'results/pdk_callback110_protocol.json').write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(cases,indent=2))
if __name__=='__main__':build()
