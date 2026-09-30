"""One-factor interface comparisons with unchanged VCO R2 and DC bias ratios."""
from pathlib import Path
import re,json
H=Path(__file__).resolve().parent

def interface(s,sampler=False,divider=False):
    if sampler:
        s=s.replace('XBM (vdd 0 vmid) tx_bias_mid','include "sampler_bias_v5.scs"\nXBM (vdd 0 vmid) tx_bias_mid_v5')
        s=s.replace('RBP (sp vmid) resistor r=100k','RBP (sp vmid) resistor r=1Meg').replace('RBN (sn vmid) resistor r=100k','RBN (sn vmid) resistor r=1Meg')
    if divider:s=s.replace('"bank_divider_light.scs"','"divider_bank_v5.scs"').replace('tx_divider_bank_light','tx_divider_bank_v5')
    return s

def main():
    conditions=[]
    for label,samp,div in [('base',False,False),('sampler',True,False),('divider',False,True),('both',True,True)]:
        s=(H.parent/'vco_v4/tb/r2_noise_divider_refined.scs').read_text()
        s=s.replace('maxstep=1p','maxstep=2p').replace('maxsideband=127','maxsideband=63').replace('saveinit=yes','saveinit=no')
        s=interface(s,samp,div)
        s=re.sub(r'^save .*$', 'save vp vn out sp sn hp hn vmid XD.icp XD.icn XD.cm XD.cim VDD:p VVCO:p',s,flags=re.M)
        (H/'tb'/f'noise_{label}.scs').write_text(s)
        t=(H.parent/'vco_v4/tb/r2_tt_k41_c6.scs').read_text();t=interface(t,samp,div)
        t=re.sub(r'^save .*$', 'save vp vn out sp sn hp hn vmid XD.icp XD.icn XD.cm XD.cim VO:p VDD:p VVCO:p',t,flags=re.M)
        (H/'tb'/f'timing_{label}.scs').write_text(t)
        conditions.append(dict(label=label,sampler=samp,divider=div,vco='R2 unchanged',noise_condition='Autonomous VCO + divide-by-4; reference DC low, sampler tracking; CP output clamped',transient_condition='24 MHz actual reference chain; fine 0.2 to 1.0 V; actual divider, sampler and CP',added_capacitance_pf=9*int(samp)+18*int(div)))
    (H/'results/screen_conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
    print('Prepared 4 noise and 4 transient comparisons')

if __name__=='__main__':main()
