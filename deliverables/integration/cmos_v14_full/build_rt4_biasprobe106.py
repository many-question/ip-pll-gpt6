"""One short conditional tuning/bias experiment after the step candidate failed."""
from pathlib import Path
import datetime, hashlib, json, re
H=Path(__file__).resolve().parent; ROOT=H.parents[3]; B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    pp=H/'results/rt4_biasprobe106_protocol.json';assert not pp.exists()
    result=json.loads((H/'results/rt4_recheckstep_detail106.json').read_text())
    assert not result['fast_capture_passed'] and result['recheck_errors']==[14,11,8,5,5,4,4,3]
    core=(B/'lc_core_physical_v14.scs').read_text().replace('lc_core_physical_v14','lc_core_biasprobe106')
    core=core.replace('(vp vn b3 b4 b5 b6 b7 vdd vss)','(vp vn b3 b4 b5 b6 b7 nfset vdd vss)')
    assert core.count('RF (nb nfilt) resistor r=1Meg')==1
    core=core.replace('RF (nb nfilt) resistor r=1Meg','// Diagnostic ideal clamp replaces RF; not a proposed production circuit.\nVNF (nfilt nfset) vsource dc=0')
    cp=B/'lc_core_biasprobe106.scs';assert not cp.exists();cp.write_text(core)
    vco=(B/'lc_vco_physical_v14.scs').read_text().replace('lc_core_physical_v14','lc_core_biasprobe106').replace('lc_vco_physical_v14','lc_vco_biasprobe106')
    vco=vco.replace('(vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vdd vss)','(vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 nfset vdd vss)')
    vco=vco.replace('XL (vp vn b3 b4 b5 b6 b7 vdd vss)','XL (vp vn b3 b4 b5 b6 b7 nfset vdd vss)')
    vp=B/'lc_vco_biasprobe106.scs';assert not vp.exists();vp.write_text(vco)
    source=H/'tb/rt4r48_range_c0_v10.scs';tb=source.read_text().replace('lc_vco_physical_v14','lc_vco_biasprobe106')
    tb=tb.replace('XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vco_vdd 0)','XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 nfset vco_vdd 0)')
    for i in range(8):tb=re.sub(r'VB%d \(b%d 0\) vsource dc=0'%(i,i),'VB%d (b%d 0) vsource dc=%s'%(i,i,'1.2' if (19>>i)&1 else '0'),tb)
    controls=[.20,.48,.84,.84,.48,.20];biases=[.728]*3+[.738]*3
    def pwl(values):
        terms=['0',str(values[0])]
        for i in range(1,len(values)):
            terms += [f'{i*400}n',str(values[i-1]),f'{i*400+.01:g}n',str(values[i])]
        return ' '.join(terms)
    tb=tb.replace('VC (ctrl 0) vsource dc=1','VC (ctrl 0) vsource type=pwl wave=['+pwl(controls)+']\nVNFSET (nfset 0) vsource type=pwl wave=['+pwl(biases)+']')
    # During FLL capture CP is disabled; preserve sampler/receiver/divider/RT4 loading.
    tb=tb.replace('VE (en 0) vsource dc=1.2','VE (en 0) vsource dc=0')
    tb=tb.replace('tran tran stop=400n start=0 outputstart=340n','tran tran stop=2400n strobeperiod=2n strobeoutput=strobeonly')
    tb+='\nahdl_include "lc_loop_observer.va"\nXOBS (vp vn refb ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer\nsave nfset obsphase obscycles obsctrl obsdivcycles\n'
    tp=H/'tb/rt4_biasprobe106_tt.scs';assert not tp.exists();tp.write_text('// Conditional diagnostic only: fixed coarse19 and externally controlled bias/tuning.\n'+tb)
    p=dict(time=datetime.datetime.now().astimezone().isoformat(),purpose=__doc__,
        cases=[dict(kind='diagnostic',case=tp.stem,run='rt4biasprobe106ssd01',stop_s=2.4e-6,tb_sha256=sha(tp))],
        segments=[dict(start_s=i*400e-9,end_s=(i+1)*400e-9,control_v=c,bias_v=b,coarse=19) for i,(c,b) in enumerate(zip(controls,biases))],
        mode='ax',maxstep_s=8e-12,reltol=.001,method='traponly',threads=2,noise=False,
        bias_choice='0.728V late and0.738V during SAR bracket observed nfilt in the completed full MOS run; these are controlled interventions, not autonomous bias operating points.',
        analysis='Compare last150ns RF/output observer frequencies at three control levels and two clamped bias levels. Verify divider ratio and within-window drift. No PLL lock inference.',
        boundary='Modified local loaded VCO fixture with ideal bias/control/coarse clamps; no full PLL/controller, no jitter, no adopted circuit modification. Purpose is causal isolation before another long capture.',
        physical_inputs_sha256={x.relative_to(ROOT).as_posix():sha(x) for x in [cp,vp,tp]},
        predecessor_review_sha256=sha(H/'results/rt4_recheckstep_detail106.json'),source_fixture_sha256=sha(source),
        resource_cap=dict(threads=18,long_jobs=4,short_jobs=1),dispatch_gate='Prior full capture fully recovered/reviewed; no owned simulations; one new short only.')
    pp.write_text(json.dumps(p,indent=2)+'\n');print(str(pp))
if __name__=='__main__':main()
