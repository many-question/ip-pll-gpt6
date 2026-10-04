"""Audit six fresh-PSS noise-on groups against the completed all-noise spectrum.

The sum limit1e-3 is a numerical consistency gate, not a project jitter spec.
No sparse spectral integration or circuit adoption is performed here.
"""
from pathlib import Path
import hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/frontend_noise_r2_all_validation.json';allv=json.loads(proof.read_text());assert allv['noise_valid']
    master=H/'results/frontend_noise_r2_all_protocol.json';p=json.loads(master.read_text());assert allv['protocol_sha256']==sha(master)
    rows=[];spectra=[];pss=[]
    for group in p['group_instances']:
        path=H/'results'/f'frontend_noise_r2_{group}_validation.json';row=dict(group=group,completed=False)
        if not path.exists():rows.append(row);continue
        v=json.loads(path.read_text());row['completed']=bool(v['periodic']['completed'])
        if not v.get('noise_valid'):row['noise_valid']=False;rows.append(row);continue
        protocol=H/'results'/f'frontend_noise_r2_{group}_protocol.json';q=json.loads(protocol.read_text())
        assert v['protocol_sha256']==sha(protocol) and q['all_noise_validation_sha256']==sha(proof)
        result=ROOT/v['periodic']['source_result'];assert sha(result)==v['periodic']['source_sha256']
        raw=result.parent/(result.parent.name+'.raw');assert sha(raw/'pn.pnoise')==v['noise_sha256']
        r=json.loads(result.read_text());assert r['ok'] and not r.get('periodic_state')
        assert v['group']==group and v['condition']==allv['condition'] and v['balanced_center_verified']
        assert np.allclose(v['offsets_hz'],allv['offsets_hz'],rtol=1e-12,atol=0)
        assert v['isolated_vs_all_group_check']['all_result_sha256']==sha(proof)
        values=np.array(v['current_psd_a2_per_hz']);spectra.append(values);pss.append(v['periodic'])
        row.update(noise_valid=True,validation_sha256=sha(path),protocol_sha256=sha(protocol),
                   source_result=v['periodic']['source_result'],source_sha256=sha(result),noise_sha256=v['noise_sha256'],
                   comparison=v['isolated_vs_all_group_check'],excluded_noise_fraction=v['excluded_noise_fraction'])
        rows.append(row)
    complete=all(x['completed'] for x in rows);valid=len(spectra)==len(p['group_instances'])
    out=dict(scope=__doc__,condition=p['condition'],all_noise_validation_sha256=sha(proof),groups=rows,complete=complete,
             passed=False,relative_sum_error_limit=1e-3,integrated_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False)
    if valid:
        total=np.array(allv['current_psd_a2_per_hz']);parts=np.array(spectra);difference=parts.sum(axis=0)/total-1
        individual=all(x['comparison']['passed'] for x in rows)
        out.update(offsets_hz=allv['offsets_hz'],independent_sum_psd_a2_per_hz=parts.sum(axis=0).tolist(),
                   relative_sum_error=difference.tolist(),max_relative_sum_error=float(max(abs(difference))),
                   individual_comparisons_passed=individual,passed=bool(individual and max(abs(difference))<out['relative_sum_error_limit']))
    out['limitations']=['Independent modules verified only at10kHz/1MHz/10MHz, TT27/1.2V and the declared idealRF/clamped platform.',
                        'A passing audit supports device attribution, not integrated fullPLL jitter, numerical convergence or PVT.']
    (H/'results/frontend_independent_audit_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
