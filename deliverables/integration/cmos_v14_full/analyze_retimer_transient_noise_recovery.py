"""Locate reported RT4 solver recovery events against source time grids."""
from pathlib import Path
import hashlib, json, re
import numpy as np

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    dst = H/'results/retimer_transient_noise_recovery_diagnosis.json'
    frozen = H/'results/retimer_transient_noise_first_on_validation.json'
    assert not dst.exists() and not frozen.exists()
    path = H/'results/retimer_transient_noise_validation.json'
    v = json.loads(path.read_text())
    c = next(x for x in v['cases'] if x['run']=='rttrannoise80g05')
    assert c['completed'] and not c['eligible_for_noise_acceptance']
    rp = ROOT/c['source_result']; assert sha(rp)==c['source_sha256']
    log = rp.parent/'spectre.out'; assert sha(log)==c['simulator_log_sha256']
    frozen.write_bytes(path.read_bytes())
    times = re.findall(r'SPECTRE-17087\): A breakpoint at time = ([0-9.]+) (ns|ps|us) is stepped over', log.read_text())
    assert len(times)==5
    dt = .5/c['source_bandwidth_hz']; tc = 1/3.936e9; td = 1/984e6
    distance = lambda t, period, edges: min(abs((t-e+period/2)%period-period/2) for e in edges)
    rows = []
    for raw, unit in times:
        scale = dict(ns=1e-9, ps=1e-12, us=1e-6)[unit]
        t = float(raw)*scale
        resolution = 10**(-len(raw.partition('.')[2]))*scale
        dg = abs(t-round(t/dt)*dt)
        rows.append(dict(logged_time_s=t, printed_resolution_s=resolution,
            noise_grid_distance_s=dg, noise_grid_within_rounding=bool(dg<=resolution/2+1e-18),
            clock_breakpoint_distance_s=distance(t,tc,[0,10e-12,tc/2,tc/2+10e-12]),
            data_breakpoint_distance_s=distance(t,td,[30e-12,40e-12,td/2+30e-12,td/2+40e-12])))
    out = dict(scope=__doc__, validation_sha256=sha(frozen), source_result_sha256=sha(rp),
        simulator_log_sha256=sha(log), source_bandwidth_hz=c['source_bandwidth_hz'],
        candidate_noise_update_grid_s=dt, events=rows,
        all_printed_events_on_grid_within_rounding=all(x['noise_grid_within_rounding'] for x in rows),
        printed_counts_are_lower_bounds=True,
        observed_band_rms_fs=c['band_rms_fs'], reference_pnoise_rms_fs=v['pnoise_expected_rms_fs'],
        observed_rms_relative_error=c['rms_relative_to_pnoise'], accepted=False,
        inference='Printed skipped breakpoints align with the candidate noise-source update grid. This suggests investigating noise generation/solver interaction before blaming device sizing. Alignment alone does not prove the internal algorithm or the physical root cause.',
        next_checks=['Complete the already owned source-bandwidth and timestep controls; inspect recovery events in every case.',
            'If recovery persists, use a separate controlled tolerance or noise-algorithm experiment with the physical DUT fixed; recheck noise-off floor and PNoise agreement.'],
        limitations=['Only five warnings are printed before suppression; their timing is rounded.',
            'A zero terminal error count and an RMS within the original10% comparison gate do not clear numerical recovery.',
            'No full10kHz-fOUT/2 or fullPLL jitter acceptance.'])
    dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__ == '__main__':
    main()
