"""Cross-check the completed original-PLL quiet trace before interpreting noise."""
from pathlib import Path
import datetime,hashlib,json
import numpy as np
from noise_utils import stream_selected

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def main():
    pp=H/'results/full_pll_main_settled_pair_protocol.json';p=json.loads(pp.read_text())
    case=p['cases'][0];d=ROOT/'research/runs/spectre_cmos_v14_full'/case['run']/case['case']
    rp=d/'result.json';r=json.loads(rp.read_text())
    vp=H/'results/full_pll_main_settled_pair_validation.json';v=json.loads(vp.read_text());q=v['cases'][0]
    assert r['ok'] and r['remote_inputs_match'] and r['state_file']['collected']
    assert q['completed'] and q['source_sha256']==sha(rp) and v['protocol_sha256']==sha(pp)
    inputs={k:sha(d/'inputs'/k) for k in r['inputs_sha256']}
    assert inputs==r['inputs_sha256']==r['remote_inputs_sha256']
    remote=json.loads((ROOT/'research/main_settled_remote_audit.json').read_text())
    outputs={k:dict(bytes=(d/k).stat().st_size,sha256=sha(d/k)) for k in remote}
    assert outputs==remote
    cache=d/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
    keys=['out','XP.vp','XP.vn','XP.refb','qualified','XP.XC.acquired','XP.XC.phase_held','XP.restart','XP.vc1']
    raw=d/(case['case']+'.raw/tran.tran.tran');a,duplicates=stream_selected(raw,keys)
    with np.load(cache) as z:
        assert all(len(z[k])==len(a['time']) for k in a)
        diffs={k:float(max(abs(values-z[k]))) for k,values in a.items()}
    assert not any(diffs.values()) and not duplicates
    m=a['time']>=p['measurement_start_s']
    summary={k:dict(min_v=float(a[k][m].min()),max_v=float(a[k][m].max()))
        for k in ['qualified','XP.XC.acquired','XP.XC.phase_held','XP.restart','XP.vc1']}
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run=case['run'],case=case['case'],
        source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),protocol_sha256=sha(pp),
        validation_at_audit_sha256=sha(vp),input_count=len(inputs),all_inputs_match=True,outputs=outputs,
        remote_local_raw_log_state_match=True,cache_sha256=sha(cache),independent_parser_samples=len(a['time']),
        independent_parser_max_differences=diffs,duplicate_records=duplicates,measurement_window_ranges=summary,
        quiet_validation=q,passed=True,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,
        limitations=['Audit pass means matching input/output evidence, not a full PLL noise pass.',
          'Quiet-gate result belongs only to this TT original-V14 operating point and its stated numerical settings.'])
    (H/'results/full_pll_main_settled_recovery_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(samples=out['independent_parser_samples'],passed=True,quiet_validation=q),indent=2))

if __name__=='__main__':main()
