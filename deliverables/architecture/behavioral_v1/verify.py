"""Independent numerical checks, executed by run.py and saved with each run."""
from dataclasses import replace
import copy
import numpy as np
from scipy import signal
from scipy.linalg import solve_discrete_lyapunov
from model import (plant, sampled_matrices, continuous_open, hybrid_reference_transfer,
                   sampled_sensitivity, partial_pulse, local_transient, points, retiming_case,
                   grid, noise_kernels, KB)


def verify(cfg, loop):
    checks = []

    def check(name, observed, limit, passed):
        checks.append({"name": name, "observed": observed, "limit": limit, "passed": bool(passed)})

    fc = cfg["loop"]["crossover_hz"]
    f = np.geomspace(1e3, 10e6, 101)
    a, b = plant(loop)
    independent = np.array([(np.linalg.solve(2j * np.pi * fi / loop.fs * np.eye(3) - a, b))[0] for fi in f])
    error = float(np.max(np.abs(independent / continuous_open(loop, f) - 1)))
    check("RC nodal-state plant agrees with impedance formula", error, 1e-9, error < 1e-9)
    crossover_error = float(abs(abs(continuous_open(loop, np.array([fc]))[0]) - 1))
    check("Synthesized continuous crossover has unity loop gain", crossover_error, 1e-10, crossover_error < 1e-10)

    fast_loop = replace(loop, fs=loop.fs * 100)
    f = np.geomspace(0.05 * fc, 5 * fc, 101)
    g = continuous_open(loop, f)
    ct = g / (1 + g)
    error = float(np.max(np.abs(hybrid_reference_transfer(fast_loop, f) / ct - 1)))
    check("Fast-sampling limit approaches continuous transfer", error, 0.015, error < 0.015)

    closed, binp, cout, e, pulse = sampled_matrices(loop)
    spectral_radius = float(max(abs(np.linalg.eigvals(closed))))
    check("Nominal exact sampled loop is stable", spectral_radius, 1, spectral_radius < 1)
    sample_var = 1e-8
    covariance = solve_discrete_lyapunov(closed, binp @ binp.T * sample_var)
    variance_exact = float((cout @ covariance @ cout.T)[0, 0])
    f = np.linspace(0, loop.fs / 2, 131073)
    h = 1 - sampled_sensitivity(loop, f)
    variance_psd = float(np.trapezoid(abs(h) ** 2 * 2 * sample_var / loop.fs, f))
    error = abs(variance_psd / variance_exact - 1)
    check("One-sided sampled PSD integral matches Lyapunov variance", error, 1e-4, error < 1e-4)
    denominator = np.real_if_close(np.poly(closed))
    wp = (loop.c1 + loop.c2) / (loop.r * loop.c1 * loop.c2)
    sensitivity_numerator = np.poly([1, 1, np.exp(-wp / loop.fs)])
    numerator = denominator - sensitivity_numerator
    numerator[0] = 0
    variances = []
    for seed in range(4):
        rng = np.random.default_rng(cfg["seed"] + seed)
        y = signal.lfilter(numerator, denominator, rng.normal(0, np.sqrt(sample_var), 2 ** 19))
        variances.append(float(np.var(y[4096:])))
    mc_error = abs(np.mean(variances) / variance_exact - 1)
    check("Four seeded white-noise runs match exact sampled variance", float(mc_error), 0.03, mc_error < 0.03)

    # Independent physical continuous-noise covariance test. Unlike the sampled
    # input check, noise is injected throughout each reference period, including
    # during the charge-pump pulse. It validates analog-noise folding and units.
    from scipy.linalg import expm
    from scipy.integrate import quad

    def cycle_average_variance(qtau):
        def propagate_noise(duration):
            block = np.block([[a, qtau], [np.zeros_like(a), -a.T]])
            transition = expm(block * duration)
            return transition[:3, 3:] @ transition[:3, :3].T
        qperiod = propagate_noise(1)
        psteady = solve_discrete_lyapunov(closed, qperiod)
        def observed_variance(tau):
            measured = expm(a * tau)[0, :] - partial_pulse(loop, tau)[0] * np.array([1., 0, 0])
            return float(measured @ psteady @ measured.T + propagate_noise(tau)[0, 0])
        return quad(observed_variance, 0, 1, points=[loop.delay, loop.delay + loop.duty], epsabs=1e-20, epsrel=1e-8)[0]

    noise_cfg = copy.deepcopy(cfg)
    noise_cfg["integration"]["low_hz"] = 1
    noise_cfg["noise"]["vco_flicker_corner_hz"] = 0
    noise_cfg["noise"]["vco_white_floor_dbc_hz"] = -1000
    fg = grid(noise_cfg, high=noise_cfg["noise"]["analog_noise_cutoff_hz"])
    nk = noise_kernels(loop, noise_cfg, fg)
    t = 1 / loop.fs
    thermal_direction = np.array([0, -loop.kv * t * t / loop.c2, loop.kv * t * t / loop.c1])
    qr = np.outer(thermal_direction, thermal_direction) * 2 * KB * (cfg["loop"]["temperature_c"] + 273.15) / (loop.r * t)
    time_variance_r = cycle_average_variance(qr)
    spectrum_variance_r = float(np.trapezoid(nk["filter_resistor"], fg))
    resistor_error = abs(spectrum_variance_r / time_variance_r - 1)
    check("Physical resistor Langevin covariance matches folded analog PSD", float(resistor_error), .005, resistor_error < .005)
    phase_A = 2 * 10 ** (cfg["noise"]["vco_close_in_l1mhz_dbc_hz"] / 10) * 1e12
    qv = np.diag([2 * np.pi ** 2 * phase_A * t, 0, 0])
    time_variance_v = cycle_average_variance(qv)
    spectrum_variance_v = float(np.trapezoid(nk["vco"], fg))
    vco_error = abs(spectrum_variance_v / time_variance_v - 1)
    check("White VCO frequency-noise covariance matches folded analog PSD", float(vco_error), .005, vco_error < .005)

    # Reconstruct the continuous pulse response at many points per reference cycle.
    # Compare its numerical Fourier transform with the harmonic-domain formula.
    cycles, oversampling = 4096, 128
    state = np.zeros((cycles, 3))
    impulse = np.zeros(cycles)
    impulse[0] = 1
    for index in range(cycles - 1):
        state[index + 1] = closed @ state[index] + binp[:, 0] * impulse[index]
    drive = impulse - state[:, 0]
    wave = np.empty((cycles, oversampling))
    for j in range(oversampling):
        tau = j / oversampling
        wave[:, j] = state @ expm(a * tau)[0, :] + partial_pulse(loop, tau)[0] * drive
    transform = np.fft.rfft(wave.ravel()) / oversampling
    freq = np.fft.rfftfreq(wave.size, 1 / (loop.fs * oversampling))
    selected = np.array([np.argmin(abs(freq - value)) for value in (5e4, 2e5, 5e5, 1e6, 2e6, 5e6, loop.fs + 5e5, 2 * loop.fs + 1e6)])
    theoretical = hybrid_reference_transfer(loop, freq[selected])
    error = float(np.max(np.abs(transform[selected] / theoretical - 1)))
    impulse_error = error
    check("Oversampled pulse impulse FFT matches baseband and images", error, 0.02, error < 0.02)

    _, trajectory = local_transient(loop, cfg, 1e-5, 0)
    linear = np.zeros_like(trajectory)
    linear[0, 0] = 1e-5
    for i in range(len(linear) - 1):
        linear[i + 1] = closed @ linear[i]
    error = float(np.max(abs(trajectory - linear)) / 1e-5)
    check("Sine detector converges to small-signal state trajectory", error, 1e-7, error < 1e-7)
    alias, _ = local_transient(loop, cfg, 0, loop.fs)
    check("Main sampler alone cannot reject adjacent reference harmonic",
          alias["last_frequency_error_hz"], loop.fs,
          abs(alias["last_frequency_error_hz"] - loop.fs) < 1 and not alias["settled_correct_harmonic"])
    high_point = points(cfg)[-1]
    good = retiming_case(cfg, high_point, .4)
    bad = retiming_case(cfg, high_point, .4, cfg["retiming"]["stress_logic_delay_ps"])
    check("Retimer preserves shared VCO time error", good["common_timing_gain"], "1 +/- 0.03", abs(good["common_timing_gain"] - 1) < .03)
    check("Retimer rejects setup-violating scenario", bad["setup_violations"], ">0 and no output jitter claim", bad["setup_violations"] > 0 and bad["retimed_raw_tie_fs"] is None)

    return {"checks": checks, "all_passed": all(c["passed"] for c in checks),
            "stochastic_reference": {"samples_per_seed": 2 ** 19, "burn_in": 4096, "seeds": 4,
                                     "sample_phase_variance": sample_var, "exact_output_phase_variance": variance_exact,
                                     "simulated_output_phase_variances": variances},
            "physical_analog_noise_crosscheck": {"resistor_time_domain_variance": time_variance_r,
                                                 "resistor_harmonic_spectrum_variance": spectrum_variance_r,
                                                 "vco_time_domain_variance": time_variance_v,
                                                 "vco_harmonic_spectrum_variance": spectrum_variance_v},
            "impulse_comparison": {"cycles": cycles, "samples_per_cycle": oversampling,
                                   "frequency_hz": freq[selected].tolist(), "relative_complex_error_max": impulse_error}}
