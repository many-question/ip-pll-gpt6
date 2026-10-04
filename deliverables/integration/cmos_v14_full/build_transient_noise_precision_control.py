"""Separate noise-source bandwidth, integration step, and finite-record RC errors."""
from pathlib import Path
import datetime, hashlib, json

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    pp = H / 'results/transient_noise_precision_protocol.json'
    assert not pp.exists()
    source = H / 'results/transient_noise_recovery_validation.json'
    previous = json.loads(source.read_text())
    assert previous['complete'] and previous['passed']
    manifest = ROOT / 'research/runs/spectre_cmos_v14_full/noiserecovercontrol01/noise_recover_rc_seed/checkpoints/at_2e-06s.json'
    cp = json.loads(manifest.read_text())
    assert cp['local_remote_hash_match'] and cp['selected_requested_time_s'] == 2e-6
    assert sha(ROOT / cp['local']) == cp['sha256']
    cases = []
    for label, bandwidth, step, seed in [
        ('10g10p', 1e10, '10p', 11),
        ('10g1p', 1e10, '1p', 11),
        ('40g1p', 4e10, '1p', 11),
        ('80g1p', 8e10, '1p', 11),
        ('80g1ps29', 8e10, '1p', 29),
    ]:
        cases.append(dict(run='noisercprecision' + label, case='noise_recover_rc_seed',
                          noisefmax=bandwidth, noisefmin=1e6, noiseseed=seed, maxstep=step))
    p = dict(scope=__doc__, time=datetime.datetime.now().astimezone().isoformat(),
             source_validation=source.name, source_validation_sha256=sha(source),
             snapshot_run='noiserecovercontrol01', checkpoint=cp['local'], checkpoint_sha256=cp['sha256'],
             condition=previous['condition'], cases=cases, resistance_ohm=1000., capacitance_f=1e-12,
             temperature_k=300.15, measurement_start_s=2.1e-6, measurement_stop_s=50.1e-6,
             tran_stop='50.1u', strobe_s=1e-10, block_s=1e-6,
             gates=dict(fine_80g_relative_variance_error=.03, bandwidth_40g_80g_relative_difference=.025,
                        mean_error_standard_errors=5),
             method='Uniform100ps samples over48us. Compare sample variance with the ideal brick-wall integral of4kTR/(1+(2*pi*f*RC)^2). Report block-variance standard error; do not reinterpret noisefmax as a proven brick-wall filter.',
             launch_scope='Five serial one-thread RC diagnostics, each300s guard in one free short slot; no circuit mutation or automatic retries.',
             main_dut_modified=False, full_pll_acceptance=False,
             limitations=previous['limitations'] + [
                 'The initial10% RC gate only established noise activation. Its systematic deficit is preserved and motivates this tighter control.',
                 'One-microsecond blocks are long relative to the1nsRC time constant; their standard error is an approximate finite-record diagnostic.',
                 'Different bandwidths/seeds need not generate paired random samples. Bandwidth comparison includes sampling uncertainty.',
                 'RC convergence does not establish MOS flicker noise, nonlinear folding, or PLL jitter accuracy.'])
    pp.write_text(json.dumps(p, indent=2) + '\n')
    print(pp)


if __name__ == '__main__':
    main()
