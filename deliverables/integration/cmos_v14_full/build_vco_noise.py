"""Current physical-bias VCO noise with the actual fixedM4 chain load.

Static reference and clamped control isolate a free-running VCO operating point.
The fixedM4 path omits other programmable branches and control/supervision.
Only XV noise is enabled; this is not closed-loop or full-DUT jitter.
"""
from pathlib import Path
import re,json,datetime
H=Path(__file__).resolve().parent
s=(H/'tb/warm_center_tt.scs').read_text().split('tran tran',1)[0]
s=re.sub(r'VR \(ref 0\) vsource[^\n]*','VR (ref 0) vsource dc=0',s)
s=s.replace('temp=27','temp=27 noiseon_inst=[XV] noiseon_type=all')
s+='VC (ctrl 0) vsource dc=0.679\ninclude "validity_physical_v14.scs"\nXDET (vp hp hn amp_good phase_good vdd 0) validity_physical_v14\n'
s+='// External fixed control/coarse bits; reference held low. No functionalVA.\nic vp=1.20001 vn=1.2\n'
for label,step,harms,side in [('coarse','1p',63,127),('fine','0.5p',127,255),('check6','0.5p',127,255)]:
 sweep='values=[10k 100k 1M 10M 100M 492M]' if label=='check6' else 'start=10k stop=492M dec=20'
 tb=s+f'''pss (out 0) pss fund=984M harms={harms} tstab=300n maxstep={step} method=traponly errpreset=conservative maxperiods=30 saveinit=no writefinal="__FINAL_STATE__"
pn (vp vn) pnoise {sweep} maxsideband={side} noiseout=[usb am pm] sweeptype=relative relharmnum=4
save vp vn clk q1 data out ctrl hp hn XV.XL.nb XV.XL.nfilt XV.XL.tail VDD:p VVCO:p VRX:p VRT:p
saveOptions options save=selected
'''
 (H/'tb'/f'vco_noise_{label}_tt.scs').write_text(tb)
(H/'results/vco_noise_protocol.json').write_text(json.dumps(dict(created=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,condition='TT27,1.2V,coarse23,control0.679V,biasR2500ohm,Q5RLC,actualfixedM4CMOSchain/10fF,referenceDC0. OnlyXVnoise.',not_closed_loop=True,not_full_programmable_load=True,precision_scope='The original full-grid fine attempt in vconoise01 was explicitly stopped after coarse runtime showed its900s budget was insufficient. Its immutable snapshot and partialdata are retained. Separately named check6 uses six offsets10k/100k/1M/10M/100M/492MHz; it is not full-grid convergence.',precision_limits=dict(max_phase_noise_delta_db=.1,max_relative_carrier_change=1e-4)),indent=2)+'\n')
print('Prepared physical VCO blocknoise, fixedM4/staticreference load, no PLL jitter claim')
