"""Validate every device record and total of the completed10kHz live-noise point."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,devices,selected_device_components
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    src=ROOT/'research/diagnostics/frontend_noise2all_first_point01';mp=src/'manifest.json';m=json.loads(mp.read_text())
    fp=src/'single_point_parser_view.pnoise';assert sha(fp)==m['parser_view_sha256']
    pp=H/'results/frontend_noise_r2_all_protocol.json';p=json.loads(pp.read_text());assert sha(pp)==m['protocol_sha256']
    proof=H/'results'/p['source_validation'];assert sha(proof)==p['source_validation_sha256']
    raw=(src/'original_partial.pnoise').read_bytes();prefix=raw[:m['prefix_bytes']]
    assert hashlib.sha256(prefix).hexdigest()==m['prefix_sha256'] and fp.read_bytes()==prefix+b'END\n'
    d=parse(fp);assert len(d['freq'])==1 and float(d['freq'][0])==1e4
    sv=d['out']**2;contrib=devices(fp,1);text=fp.read_text()
    types={n for n,b in re.findall(r'"([^\"]+)" STRUCT\((.*?)\) PROP\(',text,re.S) if '"total"' in b}
    trace=dict(re.findall(r'^"([^\"]+)" "([^\"]+)"$',text.split('\nTRACE\n',1)[1].split('\nVALUE\n',1)[0],re.M))
    expected={n for n,t in trace.items() if t in types};assert expected==set(contrib),'Incomplete device records'
    assert np.isfinite(sv[0]) and sv[0]>0;closure=float(abs(sum(contrib.values())[0]/sv[0]-1));assert closure<1e-7
    groups={g:0. for g in p['group_instances']}
    for name,value in contrib.items():
        matched=[g for g,ins in p['group_instances'].items() if any(name==x or name.startswith(x+'.') for x in ins)]
        assert len(matched)<=1
        if matched:groups[matched[0]]+=float(value[0])
        else:assert value[0]==0,(name,value)
    rank=sorted(contrib,key=lambda n:-contrib[n][0]);top=[n for n in rank[:12] if contrib[n][0]>0]
    comp=selected_device_components(fp,top,1)
    out=dict(scope=__doc__,snapshot_manifest_sha256=sha(mp),protocol_sha256=sha(pp),condition=p['condition'],phase_deg=p['phase_deg'],
             offset_hz=1e4,complete_device_records_verified=True,device_count=len(expected),device_sum_relative_error=closure,
             current_psd_a2_per_hz=float(sv[0]),current_asd_a_per_sqrt_hz=float(d['out'][0]),
             group_variance_fraction={g:x/float(sv[0]) for g,x in groups.items()},
             top_devices=[dict(device=n,variance_fraction=float(contrib[n][0]/sv[0]),components_psd_a2_per_hz={k:float(v[0]) for k,v in comp[n].items()}) for n in top],
             complete_job_result=False,noise_on_isolation_verified=False,integrated_jitter_fs=None,full_pll_acceptance=False,
             limitations=['Only one completed frequency record of a still-running simulation; no complete-noise-job claim.',
                          'All device records and sum are validated; final completed raw file must reproduce this prefix before adoption.',
                          'A10kHz ranking does not establish the dominant integrated jitter contributor.',
                          'Ideal RF and outputclamp; no actualLC noise/backaction or fullPLL transfer.'])
    dst=H/'results/frontend_noise_first_point_validation.json';assert not dst.exists();dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
