"""Check edge-spectrum scaling against independent analytic tone/white-noise powers."""
from pathlib import Path
import hashlib, json
import numpy as np
from analyze_retimer_transient_noise_control import edge_band_power

H = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    dst = H/'results/retimer_transient_noise_spectral_selfcheck.json'; assert not dst.exists()
    n, fs = 2048, 984e6; sample = np.arange(n)
    # Known power: the excluded low tone contributes zero; an interior sine A
    # contributes A^2/2, and a real Nyquist cosine B contributes B^2.
    sequence = (100e-15*np.sin(2*np.pi*3*sample/n)+20e-15*np.sin(2*np.pi*20*sample/n)
                +7e-15*np.cos(np.pi*sample)+2e-12)
    m = edge_band_power(sequence, fs, 5e6, fs/2)
    expected = (20e-15)**2/2+(7e-15)**2
    tone_error = m['variance']/expected-1
    assert abs(tone_error)<1e-10 and abs(np.mean(m['filtered']**2)/expected-1)<1e-10
    rng = np.random.default_rng(20261004); sigma = 50e-15
    measured = []
    for _ in range(2048):
        measured.append(edge_band_power(rng.normal(0, sigma, n), fs, 5e6, fs/2)['variance'])
    # Independently, IID samples have one-sided PSD2*sigma^2/fs. The final
    # real Nyquist coefficient occupies half a bin cell.
    expected_white = 2*sigma**2/fs*(m['upper']-m['lower'])
    white_error = np.mean(measured)/expected_white-1
    white_se = np.std(measured, ddof=1)/np.sqrt(len(measured))/expected_white
    assert abs(white_error)<5*white_se
    out = dict(scope=__doc__, analyzer_sha256=sha(H/'analyze_retimer_transient_noise_control.py'),
        tone_variance_s2=m['variance'], analytic_tone_variance_s2=expected, tone_relative_error=tone_error,
        iid_trials=len(measured), iid_relative_variance_error=float(white_error), iid_relative_standard_error=float(white_se),
        effective_bin_cell_band_hz=[m['lower'],m['upper']], passed=True, circuit_noise_validated=False,
        limitations=['Analytic scaling test only; does not validate Spectre, native MOS noise or a circuit result.'])
    dst.write_text(json.dumps(out, indent=2)+'\n'); print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
