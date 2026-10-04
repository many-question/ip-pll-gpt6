"""Audit native RC noise precision without promoting it to a PLL noise result."""
from pathlib import Path
import hashlib, json, re
import numpy as np
from analyze_transient_noise_recovery_control import physical

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
R = ROOT / 'research/runs/spectre_cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    pp = H / 'results/transient_noise_precision_protocol.json'
    p = json.loads(pp.read_text())
    assert sha(H / 'results' / p['source_validation']) == p['source_validation_sha256']
    assert sha(ROOT / p['checkpoint']) == p['checkpoint_sha256']
    source = R / p['snapshot_run'] / 'noise_recover_rc_seed/inputs/noise_recover_rc_seed.scs'
    original = source.read_text()
    rows = []
    for c in p['cases']:
        j = R / c['run'] / c['case']
        rp = j / 'result.json'
        supplement = j / 'completed_result.json'
        if supplement.exists():
            completed = json.loads(supplement.read_text())
            assert completed['original_client_failure_preserved']
            assert sha(rp) == completed['original_client_result_sha256']
            assert not json.loads(rp.read_text())['ok']
            rp = supplement
        row = dict(run=c['run'], case=c['case'], completed=False)
        rows.append(row)
        if not rp.exists():
            continue
        r = json.loads(rp.read_text())
        if not r.get('local_outputs_sha256'):
            continue
        row.update(completed=True, source_result=rp.relative_to(ROOT).as_posix(), source_sha256=sha(rp))
        assert r['ok'] and r['remote_inputs_match']
        assert 'spectre completes with 0 errors' in (j / 'spectre.out').read_text()
        assert all(sha(j / 'inputs' / k) == v for k, v in r['inputs_sha256'].items())
        body = (j / 'inputs' / (c['case'] + '.scs')).read_text()
        assert physical(body) == physical(original)
        assert r['native_state']['remote_hash_match'] and r['native_state']['sha256'] == p['checkpoint_sha256']
        assert r['native_state']['source_snapshot'] == p['snapshot_run']
        assert r['transient_noise_overrides'] == {k: c[k] for k in ['noisefmax', 'noisefmin', 'noiseseed']}
        assert r['numerical_overrides']['maxstep'] == c['maxstep']
        line = next(x for x in body.splitlines() if x.startswith('tran tran '))
        assert re.search(r'\bstop=' + re.escape(p['tran_stop']) + r'(?:\s|$)', line)
        cache = j / 'waveforms.npz'
        assert sha(cache) == r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:
            t, y = z['time'], z['out']
        sel = (t >= p['measurement_start_s'] - 1e-15) & (t <= p['measurement_stop_s'] + 1e-15)
        t, x = t[sel], y[sel]
        assert len(x) >= 479999 and np.allclose(np.diff(t), p['strobe_s'], rtol=1e-5, atol=1e-16)
        mean, var = float(np.mean(x)), float(np.var(x, ddof=1))
        tau = p['resistance_ohm'] * p['capacitance_f']
        ktc = 1.380649e-23 * p['temperature_k'] / p['capacitance_f']
        expected = 2 * ktc / np.pi * np.arctan(2 * np.pi * c['noisefmax'] * tau)
        block_n = round(p['block_s'] / p['strobe_s'])
        nblocks = len(x) // block_n
        blocks = x[:nblocks * block_n].reshape(nblocks, block_n)
        # Each block uses the global mean, avoiding artificial loss from fitting48 means.
        block_power = np.mean((blocks - mean)**2, axis=1)
        var_se = float(np.std(block_power, ddof=1) / np.sqrt(nblocks))
        mean_se = float(np.std(np.mean(blocks, axis=1), ddof=1) / np.sqrt(nblocks))
        row.update(noise_bandwidth_hz=c['noisefmax'], maxstep=c['maxstep'], seed=c['noiseseed'],
                   samples=len(x), blocks=nblocks, mean_v=mean, variance_v2=var, rms_v=np.sqrt(var),
                   expected_variance_v2=float(expected), kT_over_C_v2=ktc,
                   relative_variance_error=float(var / expected - 1),
                   relative_variance_standard_error=var_se / expected,
                   mean_standard_error_v=mean_se, mean_check_passed=abs(mean-1.2) <= 5*mean_se,
                   fine_precision_passed=bool(abs(var/expected-1) <= p['gates']['fine_80g_relative_variance_error']),
                   raw_cache_sha256=sha(cache))
    complete = all(x['completed'] for x in rows)
    out = dict(scope=__doc__, protocol_sha256=sha(pp), condition=p['condition'], cases=rows,
               complete=complete, precision_passed=False, full_pll_acceptance=False,
               main_dut_modified=False, limitations=p['limitations'])
    if complete:
        a, b, c, d, e = rows
        out['comparisons'] = dict(
            maxstep_1p_vs_10p_at_10g=b['variance_v2']/a['variance_v2']-1,
            bandwidth_80g_vs_40g_at_1p=d['variance_v2']/c['variance_v2']-1,
            independent_seed_29_vs_11_at_80g=e['variance_v2']/d['variance_v2']-1)
        out['precision_passed'] = bool(d['fine_precision_passed'] and e['fine_precision_passed'] and
            all(x['mean_check_passed'] for x in rows) and
            abs(out['comparisons']['bandwidth_80g_vs_40g_at_1p']) <= p['gates']['bandwidth_40g_80g_relative_difference'])
    (H / 'results/transient_noise_precision_validation.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
