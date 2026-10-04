"""Attribute actual frontend current noise, with operating-point and sum checks."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement
from noise_utils import parse,devices,selected_device_components
from build_frontend_noise_probe import CP_OBSERVATIONS

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def normalize(s):
    s=re.sub(r'^pn pnoise .*\n','',s,flags=re.M).strip()
    observation_line='save '+' '.join(CP_OBSERVATIONS)
    assert s.splitlines().count(observation_line)<=1
    s='\n'.join(line for line in s.splitlines() if line!=observation_line).strip()
    s=re.sub(r'\s+noiseon_inst=\[[^]]+\]\s+noiseon_type=all','',s)
    return re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],required=True)
    ap.add_argument('--group',default='all');choice=ap.add_mutually_exclusive_group()
    choice.add_argument('--reference-candidate',action='store_true')
    choice.add_argument('--cp-variant',choices=['fasttail','mid70']);a=ap.parse_args()
    prefix=f'cp_{a.cp_variant}_noise' if a.cp_variant else ('reference_frontend_noise' if a.reference_candidate else 'frontend_noise')
    pp=H/'results'/f'{prefix}_r{a.round}_{a.group}_protocol.json'
    if not pp.exists():print('Frontend noise protocol pending');return
    p=json.loads(pp.read_text());assert a.group=='all' or a.group in p['group_instances']
    proof=H/'results'/p['source_validation'];assert sha(proof)==p['source_validation_sha256']
    j=R/p['run']/p['case'];row=measurement(j,p['phase_deg'])
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],group=a.group,periodic=row,noise_valid=False,
             integrated_jitter_fs=None,full_pll_acceptance=False,limitations=p['limitations'])
    if row['completed']:
        r=json.loads((j/'result.json').read_text());src=R/p['source_run']/p['source_case'];old=json.loads((src/'result.json').read_text())
        assert not r.get('periodic_state')
        dep=lambda r,name:{k:v for k,v in r['inputs_sha256'].items() if k!=name+'.scs'}
        assert dep(r,j.name)==dep(old,src.name)
        assert normalize((j/'inputs'/(j.name+'.scs')).read_text())==normalize((src/'inputs'/(src.name+'.scs')).read_text())
    if row.get('periodic_passed',False):
        residual=abs(row['mean_clamp_current_a'])/p['kphi_magnitude_a_per_rf_rad']
        balanced=bool(residual<p['balanced_phase_limit_rad'] and row['amplitude_good_fraction']>.999 and row['phase_good_fraction']>.999)
        out.update(balanced_center_verified=balanced,linearized_residual_phase_rad=residual)
        if balanced:
            raw=j/(j.name+'.raw');npth=raw/'pn.pnoise';pn=parse(npth);f=pn['freq'];sv=pn['out']**2
            assert np.allclose(f,p['noise_offsets_hz'],rtol=1e-9,atol=0) and np.all(np.isfinite(sv)) and np.all(sv>0)
            d=devices(npth,len(f));closure=float(max(abs(sum(d.values())/sv-1)));assert closure<1e-7
            groups={k:np.zeros(len(f)) for k in p['group_instances']};unmapped={}
            for name,value in d.items():
                matches=[g for g,instances in p['group_instances'].items() if any(name==x or name.startswith(x+'.') for x in instances)]
                assert len(matches)<=1
                if matches:groups[matches[0]]+=value
                elif np.any(value>0):unmapped[name]=value.tolist()
            assert not unmapped,unmapped
            excluded=float(max(sum(value for group,value in groups.items() if group!=a.group)/sv)) if a.group!='all' else 0.
            assert excluded<1e-8
            gain=p['kphi_magnitude_a_per_rf_rad'];rank=sorted(d,key=lambda k:-d[k][1])
            top=[n for n in rank[:12] if np.any(d[n]>0)]
            components=selected_device_components(npth,top,len(f))
            out.update(noise_valid=True,offsets_hz=f.tolist(),current_psd_a2_per_hz=sv.tolist(),current_asd_a_per_sqrt_hz=pn['out'].tolist(),
                       equivalent_rf_phase_psd_rad2_per_hz=(sv/gain**2).tolist(),kphi_magnitude_a_per_rf_rad=gain,
                       group_psd_a2_per_hz={g:v.tolist() for g,v in groups.items()},group_variance_fraction={g:(v/sv).tolist() for g,v in groups.items()},
                       device_sum_relative_error=closure,excluded_noise_fraction=excluded,noise_sha256=sha(npth),
                       top_devices_at_1mhz=[dict(device=n,fraction=float(d[n][1]/sv[1]),psd_a2_per_hz=d[n].tolist()) for n in top],
                       top_device_components_a2_per_hz={n:{k:v.tolist() for k,v in values.items()} for n,values in components.items()})
            if a.group!='all':
                allpath=H/'results'/f'{prefix}_r{a.round}_all_validation.json';allv=json.loads(allpath.read_text());assert allv['noise_valid']
                assert allpath.name==p['all_noise_validation'] and sha(allpath)==p['all_noise_validation_sha256']
                baseline=np.array(allv['group_psd_a2_per_hz'][a.group]);assert np.all(baseline>0)
                delta=10*np.log10(sv/baseline)
                out['isolated_vs_all_group_check']=dict(all_result_sha256=sha(allpath),psd_change_db=delta.tolist(),passed=bool(max(abs(delta))<.1))
    if a.reference_candidate:out['candidate_block_sha256']=p['candidate_block_sha256']
    if a.cp_variant:out['cp_variant']=p['cp_variant']
    dst=H/'results'/f'{prefix}_r{a.round}_{a.group}_validation.json';dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='top_device_components_a2_per_hz'},indent=2))

if __name__=='__main__':main()
