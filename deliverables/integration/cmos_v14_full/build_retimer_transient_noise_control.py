"""Prepare a native-transient device-noise cross-check of the measured TT RT4."""
from pathlib import Path
import datetime, hashlib, json, re

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    pp = H/'results/retimer_transient_noise_protocol.json'
    assert not pp.exists()
    proof = H/'results/retimer_standalone_band_validation.json'
    v = json.loads(proof.read_text()); assert v['precision_passed']
    source = next(c for c in v['cases'] if c['grade'] == 'finer')
    result = ROOT/source['source_result']; assert sha(result) == source['source_sha256']
    manifest = json.loads(result.read_text())
    body = (result.parent/'inputs'/(source['case']+'.scs')).read_text()
    body = re.sub(r'^(pss |pn |edge |save ).*\n', '', body, flags=re.M)
    # Only analyses, observation list, and numerical tolerances differ.
    body = body.replace('reltol=1e-5 vabstol=1e-7 iabstol=1e-13',
                        'reltol=1e-6 vabstol=1e-9 iabstol=1e-15')
    body += ('\nsave out\n'
        'tran tran stop=100n maxstep=0.5p method=traponly errpreset=conservative '
        'noisefmax=0 noisefmin=1M noiseseed=11 savefile="__NATIVE_SAVE__" '
        'savetime=[100n] writefinal="__FINAL_STATE__"\n')
    name = 'retimer_tran_noise_seed_tt'
    tb = H/'tb'/(name+'.scs'); assert not tb.exists()
    tb.write_text(body, encoding='utf-8', newline='\n')
    cases = []
    for label, bandwidth, step, seed in [
        ('off05', 0., '0.5p', 11), ('off025', 0., '0.25p', 11),
        ('80g05', 8e10, '0.5p', 11), ('160g05', 1.6e11, '0.5p', 11),
        ('160g025', 1.6e11, '0.25p', 11), ('160g025s29', 1.6e11, '0.25p', 29),
    ]:
        cases.append(dict(run='rttrannoise'+label, case=name, noisefmax=bandwidth,
                          noisefmin=1e6, noiseseed=seed, maxstep=step))
    p = dict(scope=__doc__, time=datetime.datetime.now().astimezone().isoformat(),
        condition=v['condition'], source_validation=proof.name, source_validation_sha256=sha(proof),
        source_result=source['source_result'], source_sha256=source['source_sha256'],
        source_noise_sha256=source['noise_sha256'], seed_run='rttrannoiseseed01', case=name,
        seed_tb_sha256=sha(tb), seed_time_s=1e-7, tran_stop='2.3u', measurement_start_s=2e-7,
        edge_count=2048, edge_threshold_v=.6, output_hz=984e6,
        comparison_band_hz=[5e6, 492e6], cases=cases,
        dependencies_sha256={k: v for k, v in manifest['inputs_sha256'].items() if k!=source['case']+'.scs'},
        gate=dict(noiseless_edge_rms_fs=5., noiseless_step_difference_rms_fs=5.,
                  noise_rms_relative_pnoise_error=.10, refined_rms_relative_change=.05),
        analysis='Pair2048 consecutive rising output edges after200ns against the0.25ps noiseless run. Uniform edge-index periodogram of timing residuals, exactFFT-bin integration5MHz..492MHz. Compare with the previously verified sampled-PNoise PSD integrated over the identical bin cells. No fictitious interpolation of a short trace to10kHz.',
        launch_scope='After RC precision review passes: one100ns seed and six serial native branches, one short slot, one thread, each1200s client guard; no retries or DUT adoption.',
        main_dut_modified=False, full_pll_acceptance=False,
        limitations=['Standalone RT4 only; ideal noiseless sources and10fF, not complete PLL jitter.',
            '2048 cycles resolve about480kHz; this finite-record comparison excludes offsets below5MHz.',
            'Noisefmin1MHz is a source spectrum corner, not the analysis highpass cutoff.',
            'A single short trace has statistical error; report block-variance scatter and two independent noise seeds.',
            'PNoise comparison is a linearized reference; nonlinear interactions and source-bandwidth convergence must be observed.',
            'Noise-off subtraction removes the measured deterministic edge schedule; no rescaling or noise inflation.'])
    pp.write_text(json.dumps(p, indent=2)+'\n'); print(pp)


if __name__ == '__main__':
    main()
