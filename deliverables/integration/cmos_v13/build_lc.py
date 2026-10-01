"""Build an actual LC fixed-control test from a functionally passing RF fixture."""
from pathlib import Path
import argparse,datetime,json,re
H=Path(__file__).resolve().parent;D=H.parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--template',required=True);p.add_argument('--label',required=True)
    p.add_argument('--code',type=int,required=True);p.add_argument('--control',type=float,default=.6)
    p.add_argument('--bias',type=int,default=100);p.add_argument('--corner',default='tt')
    p.add_argument('--temperature',type=int,default=27);p.add_argument('--fine',action='store_true')
    a=p.parse_args();assert 0<=a.code<256
    rows=json.loads((H/'results/validation.json').read_text())
    row=next(r for r in rows if r['case']==a.template)
    assert row['wave']['pass_function'],'Actual LC candidate requires passing source-fixture function'
    body=(H/'tb'/f'{a.template}.scs').read_text()
    chain='include "rf_'+body.split('include "rf_',1)[1]
    chain=re.split(r'\b(?:pss pss|tran tran)',chain)[0]
    prefix=(D/'integration/vco_v4/tb/r2_tt_k41_c6.scs').read_text().split('include "lc_vco_v4r.scs"')[0]
    old=(D/'integration/accuracy_v7/tb/clamp8_mid_pss.scs').read_text()
    sampler='include "cp_experiment.scs"'+old.split('include "cp_experiment.scs"')[1].split('XD (vp')[0]
    sampler=sampler.replace('XR (ref refb','XREF (ref refb').replace('VO (cpout ctrl) vsource dc=0','VO (cpout 0) vsource dc=.6')
    s=prefix+'include "lc_vco_repaired.scs"\nVDD (vdd 0) vsource dc=1.2\nVVCO (vco_vdd vdd) vsource dc=0\n'+f'VC (ctrl 0) vsource dc={a.control}\n'
    for bit in range(8):s+=f'VB{bit} (b{bit} 0) vsource dc={1.2 if (a.code>>bit)&1 else 0}\n'
    s+=f'XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vco_vdd 0) tx_lc_vco_repaired ibias={a.bias}u\n'+sampler+chain
    s+='ic vp=1.20001 vn=1.2\ntran tran stop=400n start=0 outputstart=340n maxstep='+('.5p' if a.fine else '1p')+' method=traponly errpreset=conservative writefinal="__FINAL_STATE__"\n'
    s+='save vp vn clk q1 data out ctrl sp sn hp hn refb XV.XL.nb XV.XL.nfilt XV.XL.tail VDD:p VVCO:p VRX:p VRT:p\nsaveOptions options save=selected\n'
    s=s.replace('section=tt\n',f'section={a.corner}\n').replace('section=tt_bbmvar',f'section={a.corner}_bbmvar').replace('temp=27',f'temp={a.temperature}')
    name=f'lc_{a.label}_c{a.code}_v{str(a.control).replace(".","p")}_i{a.bias}_{a.corner}'+('_fine' if a.fine else '')
    path=H/'tb'/f'{name}.scs';assert not path.exists();path.write_text(s,encoding='utf-8',newline='\n')
    protocol=dict(time=datetime.datetime.now().astimezone().isoformat(),case=name,parameters=vars(a),
        scope='Actual Q5 R2 LC, sampler/CP/reference buffer, selected CMOS receiver/divider/retimer. Fixed control/CPclamp, not closed PLL or cold-supply startup. Bias source ideal.',
        limits='Original measuredRF /4 frequency and swing criteria; mean frequency change<0.1%,mean power<1% on1ps/.5ps paired precision. Save60ns covers>one24MHz reference period.')
    (H/'results'/f'protocol_{name}.json').write_text(json.dumps(protocol,indent=2)+'\n');print(name)


if __name__=='__main__':main()
