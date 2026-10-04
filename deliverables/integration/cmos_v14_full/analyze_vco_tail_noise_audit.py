"""Check isolated VCO groups against all-noise contributions and sum closure."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,devices
from analyze_vco_bias_band import read

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def normalized(s):
    s=s.replace('values=[1M 10M 100M]','start=10k stop=492M dec=20')
    s=re.sub(r'noiseon_inst=\[[^]]+\]','noiseon_inst=[GROUP]',s)
    return re.sub(r'writefinal="[^"]+"','writefinal="STATE"',s)

def main():
    pp=H/'results/vco_tail_noise_audit_protocol.json';p=json.loads(pp.read_text());proof=H/'results'/p['source_validation'];assert sha(proof)==p['source_validation_sha256']
    src=R/p['source_run']/p['source_case'];base,bs=read(src);br=json.loads((src/'result.json').read_text());raw=src/(src.name+'.raw')
    ix=[int(np.argmin(abs(bs['f']/f-1))) for f in p['offsets_hz']];assert np.allclose(bs['f'][ix],p['offsets_hz'],rtol=1e-9,atol=0)
    rows=[];spectra=[];base_time=2*bs['L'][ix]/(2*np.pi*base['rf_hz'])**2
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json';row=dict(group=c['group'],case=c['case'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(row);continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text();row.update(completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp))
        ok=bool(r['ok'] and 'spectre completes with 0 errors' in log and 'steady-state solution was achieved' in log)
        row['simulation_passed']=ok
        if not ok:rows.append(row);continue
        assert r['remote_inputs_match'] and not r.get('periodic_state') and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        dep=lambda x,case:{k:v for k,v in x['inputs_sha256'].items() if k!=case+'.scs'}
        assert dep(r,j.name)==dep(br,src.name)
        assert normalized((j/'inputs'/(j.name+'.scs')).read_text())==normalized((src/'inputs'/(src.name+'.scs')).read_text())
        jr=j/(j.name+'.raw');fd=parse(jr/'pss.fd.pss');td=parse(jr/'pss.td.pss');pn=parse(jr/'pn.pm.pnoise')
        f=pn['relative frequency'];assert np.allclose(f,p['offsets_hz'],rtol=1e-9,atol=0)
        fc=float(fd['freq'][4]);peak=float(abs(fd['vp'][4]-fd['vn'][4]));cp=peak**2/2;t=td['time'];T=t[-1]-t[0]
        harmonics={n:int(1+np.argmax(abs(fd[n][1:]))) for n in ['vp','vn','clk','q1','data','out']}
        endpoint=max(float(abs(td[n][-1]-td[n][0])) for n in harmonics)
        periodic=bool(harmonics==dict(vp=4,vn=4,clk=4,q1=2,data=1,out=1) and abs(fc*T/4-1)<1e-8 and endpoint<1e-3)
        carrier_td=float(abs(2/T*np.trapezoid((td['vp']-td['vn'])*np.exp(-2j*np.pi*4*(t-t[0])/T),t)))
        assert abs(carrier_td/peak-1)<.002
        dev=devices(jr/'pn.pm.pnoise',len(f));total=pn['out']**2;closure=float(max(abs(sum(dev.values())/total-1)));assert closure<1e-7
        allowed=p['group_instances'][c['group']]
        excluded=float(max(np.asarray(sum(value for name,value in dev.items() if not any(name==x or name.startswith(x+'.') for x in allowed)))/total));assert excluded<1e-8
        st=2*total/cp/(2*np.pi*fc)**2
        reference=2*sum(bs['parts'][name][ix] for name in p['positive_sources'][c['group']])/(2*np.pi*base['rf_hz'])**2
        delta=10*np.log10(st/reference);fr=fc/base['rf_hz']-1;lim=p['limits']
        passed=bool(periodic and abs(fr)<lim['max_relative_rf_change'] and max(abs(delta))<lim['max_group_psd_difference_db'])
        row.update(physical_comparison_verified=True,rf_hz=fc,relative_rf_change=fr,periodic_passed=periodic,
            endpoint_max_v=endpoint,dominant_harmonics=harmonics,rf_carrier_peak_v=peak,psd_comparison_db=delta.tolist(),passed=passed,
            timing_psd_s2_per_hz=st.tolist(),excluded_noise_fraction=excluded,device_sum_relative_error=closure,
            noise_sha256=sha(jr/'pn.pm.pnoise'),td_sha256=sha(jr/'pss.td.pss'),fd_sha256=sha(jr/'pss.fd.pss'))
        rows.append(row);spectra.append(st)
    complete=all(r['completed'] for r in rows);out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],offsets_hz=p['offsets_hz'],
        cases=rows,complete=complete,passed=False,integrated_jitter_fs=None,full_pll_acceptance=False,limitations=p['limitations'])
    if complete and len(spectra)==len(rows):
        error=float(max(abs(sum(spectra)/base_time-1)));out.update(independent_group_sum_relative_error=error,
            passed=bool(all(x['passed'] for x in rows) and error<p['limits']['max_closure_relative_error']))
    (H/'results/vco_tail_noise_audit_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
