"""Audit the completed short probe without assigning an integrated jitter value."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
from noise_utils import stream_selected

H=Path(__file__).resolve().parent
ROOT=H.parents[3]

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def main():
    pp=H/'results/full_pll_noise_activation_probe_protocol.json'
    protocol=json.loads(pp.read_text())
    directory=ROOT/'research/runs/spectre_cmos_v14_full'/protocol['run']/protocol['case']
    result_path=directory/'completed_result.json'
    result=json.loads(result_path.read_text())
    validation_path=H/'results/full_pll_noise_activation_probe_validation.json'
    validation=json.loads(validation_path.read_text())
    assert result['ok'] and result['original_client_failure_preserved']
    assert sha(directory/'result.json')==result['original_client_result_sha256']
    assert validation['source_result_sha256']==sha(result_path)
    assert validation['protocol_sha256']==sha(pp)
    input_hashes={name:sha(directory/'inputs'/name) for name in result['inputs_sha256']}
    assert input_hashes==result['inputs_sha256']==result['remote_inputs_sha256']
    outputs={name:dict(sha256=sha(directory/name),bytes=(directory/name).stat().st_size)
             for name in result['remote_outputs_sha256']}
    assert {k:v['sha256'] for k,v in outputs.items()}==result['remote_outputs_sha256']
    cache=directory/'waveforms.npz'
    assert sha(cache)==result['local_outputs_sha256']['waveforms.npz']
    keys=['out','qualified','frequency_good','XP.XC.phase_held','XP.XC.acquired','XP.restart','range_error']
    raw=directory/(protocol['case']+'.raw/tran.tran.tran')
    independent,duplicates=stream_selected(raw,keys)
    with np.load(cache) as saved:
        differences={k:float(np.max(np.abs(values-saved[k]))) for k,values in independent.items()}
        assert all(len(saved[k])==len(independent['time']) for k in independent)
    assert all(v==0 for v in differences.values()) and duplicates==0
    assert validation['activation_method_passed'] and not validation['passed']
    assert not validation['full_pll_acceptance'] and validation['integrated_jitter_fs'] is None
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),
        source_result=result_path.relative_to(ROOT).as_posix(),source_result_sha256=sha(result_path),
        original_timeout_sha256=result['original_client_result_sha256'],
        original_timeout_preserved=True,validation_sha256=sha(validation_path),
        input_count=len(input_hashes),all_inputs_match=True,outputs=outputs,
        remote_local_raw_match=True,cache_sha256=sha(cache),independent_parser_compared_signals=list(independent),
        independent_parser_samples=len(independent['time']),duplicate_records=duplicates,
        independent_parser_max_differences=differences,start_s=float(independent['time'][0]),
        stop_s=float(independent['time'][-1]),passed=True,full_pll_acceptance=False,integrated_jitter_fs=None)
    (H/'results/full_pll_noise_activation_recovery_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
