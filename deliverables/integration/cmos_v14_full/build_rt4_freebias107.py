"""One short neighboring-code check with the real VCO bias network restored."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    pp=H/'results/rt4_freebias107_protocol.json';assert not pp.exists()
    prior=H/'results/rt4_biasprobe107_review.json';d=json.loads(prior.read_text())
    assert d['finite'] and all(x['rf_change_mhz'] < -19 for x in d['bias_shift_mhz'])
    source=H/'tb/rt4r48_range_c0_v10.scs';s=source.read_text()
    assert 'include "lc_vco_physical_v14.scs"' in s
    for i in range(8):
        a='1.2' if (19>>i)&1 else '0';b='1.2' if (20>>i)&1 else '0'
        s=re.sub(r'VB%d \(b%d 0\) vsource dc=0'%(i,i),f'VB{i} (b{i} 0) vsource type=pwl wave=[0 {a} 1000n {a} 1000.01n {b}]',s)
    s=s.replace('VC (ctrl 0) vsource dc=1','VC (ctrl 0) vsource type=pwl wave=[0 .2 2000n .2 2000.01n .84]')
    s=s.replace('VE (en 0) vsource dc=1.2','VE (en 0) vsource dc=0')
    s=s.replace('ic vp=1.20001 vn=1.2','// Diagnostic warm bias IC from completed full record; released at t=0, not clamped.\nic vp=1.20001 vn=1.2 XV.XL.nfilt=.728')
    s=s.replace('tran tran stop=400n start=0 outputstart=340n','tran tran stop=3u strobeperiod=2n strobeoutput=strobeonly')
    s+='\nahdl_include "lc_loop_observer.va"\nXOBS (vp vn refb ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer\nsave obsphase obscycles obsctrl obsdivcycles\n'
    tp=H/'tb/rt4_freebias107_tt.scs';assert not tp.exists();tp.write_text('// Local diagnostic only, no controller. Original real RF/CF bias network.\n'+s)
    p=dict(time=datetime.datetime.now().astimezone().isoformat(),purpose=__doc__,cases=[dict(kind='diagnostic',case=tp.stem,run='rt4freebias107ssd01',stop_s=3e-6,tb_sha256=sha(tp))],
      segments=[dict(start_s=0,end_s=1e-6,coarse=19,control_v=.2),dict(start_s=1e-6,end_s=2e-6,coarse=20,control_v=.2),dict(start_s=2e-6,end_s=3e-6,coarse=20,control_v=.84)],
      mode='ax',maxstep_s=8e-12,reltol=.001,method='traponly',threads=2,noise=False,strobe_period_s=2e-9,expected_points=1501,
      initialization='Only differential10uV seed and nfilt=.728V IC, released at t=0; original1Meg/10p bias network retained. Fixed code/control fixture, no FLL/PLL lock claim.',
      analysis='Last300ns per segment: RF/output crossing observer, divider ratio, nfilt range/drift. Compare target3936MHz and current19/adjacent20 coverage. Short observation is not asymptotic steady-state signoff.',
      predecessor_review_sha256=sha(prior),source_fixture_sha256=sha(source),physical_inputs_sha256={tp.relative_to(ROOT).as_posix():sha(tp)},
      boundary='Local loaded RT4 VCO fixture; original VCO bias circuit restored, but externally fixed codes/control and warm bias IC. Not full PLL capture or adopted code change. No inherited noise/lock pass.',
      resource_cap=dict(threads=18,long_jobs=4,short_jobs=1),dispatch_gate='Previous conditional diagnostic fully collected and independently audited, no owned jobs; one new3us short only.')
    pp.write_text(json.dumps(p,indent=2)+'\n');print(str(pp))
if __name__=='__main__':main()
