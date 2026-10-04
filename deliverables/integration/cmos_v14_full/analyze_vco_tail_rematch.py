"""Measure a two-point physical tuning bracket; interpolation is a proposal."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/vco_tail_rematch_protocol.json';p=json.loads(pp.read_text());rows=[]
    base=R/'vcotail560_01/vco_bias_cf40_tail560_tt';br=json.loads((base/'result.json').read_text())
    for spec in p['cases']:
        j=R/p['run']/spec['case'];rp=j/'result.json'
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        assert r['ok'] and r['remote_inputs_match'] and not r.get('periodic_state')
        assert 'spectre completes with 0 errors' in log and 'The steady-state solution was achieved' in log
        assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}=={k:v for k,v in br['inputs_sha256'].items() if k!=base.name+'.scs'}
        def normal(s):return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)
        original=(base/'inputs'/(base.name+'.scs')).read_text()
        expected=re.sub(r'^pn .*\n','',original,flags=re.M).replace('VB1 (b1 0) vsource dc=1.2','VB1 (b1 0) vsource dc=0').replace('VC (ctrl 0) vsource dc=0.679',f"VC (ctrl 0) vsource dc={spec['control_v']:g}")
        assert normal(expected)==normal((j/'inputs'/(j.name+'.scs')).read_text())
        raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0];fc=float(fd['freq'][4])
        harmonics={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/fd['freq'][1])) for k in ['vp','vn','clk','q1','data','out']}
        endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in harmonics)
        assert harmonics==dict(vp=4,vn=4,clk=4,q1=2,data=1,out=1) and abs(fc*T/4-1)<1e-8 and endpoint<1e-3
        assert max(abs(td['ctrl']-spec['control_v']))<1e-10
        peak=float(abs(fd['vp'][4]-fd['vn'][4]));timepeak=float(abs(2/T*np.trapezoid((td['vp']-td['vn'])*np.exp(-2j*np.pi*4*(t-t[0])/T),t)))
        assert abs(timepeak/peak-1)<.002
        rows.append(dict(case=j.name,control_v=spec['control_v'],coarse_code=21,rf_hz=fc,carrier_peak_v=peak,
            vco_supply_mw=float(-1.2*np.trapezoid(td['VVCO:p'],t)/T*1e3),endpoint_max_v=endpoint,periodic_passed=True,
            source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),raw_fd_sha256=sha(raw/'pss.fd.pss')))
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],cases=rows,complete=len(rows)==2,
        target_rf_hz=p['target_rf_hz'],frequency_bracketed=False,proposed_control_v=None,matched_point_measured=False,
        noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    if len(rows)==2:
        lo,hi=sorted(rows,key=lambda x:x['rf_hz']);target=p['target_rf_hz']
        if lo['rf_hz']<=target<=hi['rf_hz']:
            value=lo['control_v']+(target-lo['rf_hz'])/(hi['rf_hz']-lo['rf_hz'])*(hi['control_v']-lo['control_v'])
            assert p['limits']['control_v'][0]<=value<=p['limits']['control_v'][1]
            out.update(frequency_bracketed=True,proposed_control_v=value,
                secant_gain_hz_per_v=(hi['rf_hz']-lo['rf_hz'])/(hi['control_v']-lo['control_v']))
    (H/'results/vco_tail_rematch_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
