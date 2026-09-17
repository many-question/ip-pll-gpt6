"""SSPLL third-order passive-filter and exact sampled rectangular-pulse model.

Small signal noise is cycle-averaged, including alias feedback and pulse images.
No transistor data, spur, autonomous FLL, supply coupling, or extracted parasitics.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np
from scipy.linalg import expm
from scipy.integrate import cumulative_trapezoid

KB = 1.380649e-23


@dataclass(frozen=True)
class Loop:
    fs: float
    kpd: float
    kv: float
    r: float
    c1: float
    c2: float
    duty: float
    delay: float
    latency: int = 0


def synthesize(cfg, fc=None):
    p = cfg["loop"]
    fc = p["crossover_hz"] if fc is None else fc
    wz = 2 * np.pi * fc * p["zero_to_crossover_ratio"]
    wp = 2 * np.pi * fc * p["pole_to_crossover_ratio"]
    wc = 2 * np.pi * fc
    kv = 2 * np.pi * p["kvco_hz_per_v"]
    total = p["kpd_average_a_per_rad"] * kv * np.sqrt(1 + (wc / wz) ** 2) / (wc ** 2 * np.sqrt(1 + (wc / wp) ** 2))
    c2 = total * wz / wp
    c1 = total - c2
    return Loop(cfg["reference_hz"], p["kpd_average_a_per_rad"], kv, 1 / (wz * c1), c1, c2,
                p["pulse_duty"], p["pulse_delay_cycles"], p["extra_delay_cycles"])


def impedance(loop, f):
    s = 2j * np.pi * np.asarray(f)
    return (1 + s * loop.r * loop.c1) / (s * (loop.c1 + loop.c2) + s ** 2 * loop.r * loop.c1 * loop.c2)


def continuous_open(loop, f):
    return loop.kpd * loop.kv * impedance(loop, f) / (2j * np.pi * np.asarray(f))


def plant(loop):
    # State [phase, Kv*T*vcontrol, Kv*T*vC1]; time coordinate tau=t/T.
    t = 1 / loop.fs
    a = np.array([[0, 1, 0], [0, -t / (loop.r * loop.c2), t / (loop.r * loop.c2)],
                  [0, t / (loop.r * loop.c1), -t / (loop.r * loop.c1)]])
    b = np.array([0, loop.kv * t * t * loop.kpd / loop.c2, 0])
    return a, b


def transition(a, b, duration):
    augmented = np.zeros((4, 4))
    augmented[:3, :3] = a
    augmented[:3, 3] = b
    result = expm(augmented * duration)
    return result[:3, :3], result[:3, 3]


def partial_pulse(loop, tau):
    a, b = plant(loop)
    end = min(tau, loop.delay + loop.duty)
    width = max(0, end - loop.delay)
    if width == 0:
        return np.zeros(3)
    return expm(a * (tau - end)) @ transition(a, b, width)[1] / loop.duty


def sampled_matrices(loop):
    assert 0 < loop.duty <= 1 and 0 <= loop.delay and loop.delay + loop.duty <= 1
    assert loop.latency in (0, 1)
    a, b = plant(loop)
    e = expm(a)
    pulse = partial_pulse(loop, 1)
    c = np.array([1., 0, 0])
    if loop.latency == 0:
        return e - np.outer(pulse, c), pulse[:, None], c[None, :], e, pulse
    f = np.zeros((4, 4))
    f[:3, :3] = e
    f[:3, 3] = pulse
    f[3, 0] = -1
    return f, np.array([[0.], [0], [0], [1]]), np.array([[1., 0, 0, 0]]), e, pulse


def sampled_sensitivity(loop, f):
    # Exact determinant ratio avoids cancellation of 1-H near DC.
    closed, _, _, _, _ = sampled_matrices(loop)
    z = np.exp(2j * np.pi * np.asarray(f) / loop.fs)
    wp = (loop.c1 + loop.c2) / (loop.r * loop.c1 * loop.c2)
    numerator = (z - 1) ** 2 * (z - np.exp(-wp / loop.fs)) * z ** loop.latency
    denominator = np.prod(z[..., None] - np.linalg.eigvals(closed), axis=-1)
    return numerator / denominator


def hybrid_reference_transfer(loop, f):
    f = np.asarray(f)
    pulse_shape = np.sinc(f * loop.duty / loop.fs) * np.exp(-2j * np.pi * f / loop.fs * (loop.delay + loop.duty / 2 + loop.latency))
    return continuous_open(loop, f) * pulse_shape * sampled_sensitivity(loop, f)


def alias_frequency(f, fs):
    return np.abs((np.asarray(f) + fs / 2) % fs - fs / 2)


def grid(cfg, high=None, multiplier=1):
    low = cfg["integration"]["low_hz"]
    high = 984e6 / 2 if high is None else high
    fs = cfg["reference_hz"]
    # Explicit neighborhoods resolve sampled-loop features around reference harmonics.
    local = np.geomspace(100, fs / 2, 180 * multiplier)
    parts = [np.geomspace(low, high, cfg["integration"]["grid_points"] * multiplier)]
    for center in np.arange(0, high + fs, fs):
        parts.extend([center - local, center + local])
    parts.append(np.array([10e6] + [k * 12e6 for k in range(9, 42)]))
    result = np.unique(np.concatenate(parts))
    return result[(result >= low) & (result <= high)]


def analog_phase_sources(loop, cfg, f):
    noise = cfg["noise"]
    raw = np.abs(np.asarray(f))
    f = np.maximum(raw, noise["source_regularization_hz"])
    vco = 2 * (10 ** (noise["vco_close_in_l1mhz_dbc_hz"] / 10) * (1e6 / f) ** 2
               * (1 + noise["vco_flicker_corner_hz"] / f) / (1 + noise["vco_flicker_corner_hz"] / 1e6)
               + 10 ** (noise["vco_white_floor_dbc_hz"] / 10))
    thermal_v = 4 * KB * (cfg["loop"]["temperature_c"] + 273.15) * np.real(impedance(loop, f))
    resistor = (loop.kv / (2 * np.pi * f)) ** 2 * thermal_v
    mask = raw <= noise["analog_noise_cutoff_hz"]
    return {"vco": vco * mask, "filter_resistor": resistor * mask}


def noise_kernels(loop, cfg, f, method="hybrid"):
    n = cfg["noise"]
    if method == "hybrid":
        h = hybrid_reference_transfer(loop, f)
    else:
        g = continuous_open(loop, f)
        h = g / (1 + g)
    h2 = np.abs(h) ** 2
    temperature = cfg["loop"]["temperature_c"] + 273.15
    fa = np.maximum(alias_frequency(f, loop.fs) if method == "hybrid" else f, n["source_regularization_hz"])
    sampler_var_phase = 2 * KB * temperature / n["sampling_capacitance_each_f"] / n["detector_differential_slope_v_per_rad"] ** 2
    kernels = {
        "reference": h2 * (n["reference_time_asd_as_per_sqrt_hz"] * 1e-18) ** 2 * (1 + n["reference_flicker_corner_hz"] / fa),
        "reference_buffer": h2 * (n["reference_buffer_time_asd_as_per_sqrt_hz"] * 1e-18) ** 2,
        "sampler": h2 * 2 * sampler_var_phase / loop.fs,
        "charge_pump": h2 * (n["cp_period_average_current_asd_a_per_sqrt_hz"] / loop.kpd) ** 2,
        "retimer": np.full_like(f, (n["retimer_time_asd_as_per_sqrt_hz"] * 1e-18) ** 2),
        "output_buffer": np.full_like(f, (n["output_buffer_time_asd_as_per_sqrt_hz"] * 1e-18) ** 2)
    }
    direct = analog_phase_sources(loop, cfg, f)
    aliases = {key: np.zeros_like(f) for key in direct}
    if method == "hybrid":
        limit = int(np.ceil((n["analog_noise_cutoff_hz"] + f[-1]) / loop.fs))
        for shift in range(-limit, limit + 1):
            if shift:
                shifted = analog_phase_sources(loop, cfg, f + shift * loop.fs)
                for key in aliases:
                    aliases[key] += shifted[key]
    for key in direct:
        kernels[key] = np.abs(1 - h) ** 2 * direct[key] + h2 * aliases[key]
    return kernels


PHASE_SOURCES = {"sampler", "charge_pump", "vco", "filter_resistor"}


def points(cfg):
    return [{"k": k, "m": m, "n": k * m, "fout_hz": k * cfg["reference_hz"], "fvco_hz": k * m * cfg["reference_hz"]}
            for start, end, m in cfg["frequency_groups"] for k in range(start, end + 1)]


def integrate_points(cfg, f, kernels, fc, method="hybrid"):
    integrated = {key: cumulative_trapezoid(value, f, initial=0) for key, value in kernels.items()}
    rows = []
    for point in points(cfg):
        for label, high in [("10k_to_10M", cfg["integration"]["fixed_high_hz"]), ("10k_to_fout_over_2", point["fout_hz"] / 2)]:
            row = {**point, "method": method, "design_crossover_hz": fc, "window": label, "high_hz": high}
            total = 0
            for key, values in integrated.items():
                variance = float(np.interp(high, f, values))
                if key in PHASE_SOURCES:
                    variance /= (2 * np.pi * point["fvco_hz"]) ** 2
                row[key + "_fs"] = np.sqrt(variance) * 1e15
                total += variance
            row["total_fs"] = np.sqrt(total) * 1e15
            row["below_200fs_in_hypothesis"] = row["total_fs"] < 200
            rows.append(row)
    return rows


def local_transient(loop, cfg, phase0, frequency_error):
    assert loop.latency == 0
    _, _, _, e, b = sampled_matrices(loop)
    n = cfg["transient"]["samples"]
    x = np.zeros((n, 3))
    x[0, 0] = phase0
    advance = np.array([2 * np.pi * frequency_error / loop.fs, 0, 0])
    for i in range(n - 1):
        x[i + 1] = e @ x[i] - b * np.sin(x[i, 0]) + advance
    phase = np.angle(np.exp(1j * x[:, 0]))
    vcontrol = x[:, 1] * loop.fs / loop.kv
    # Unwrapped phase advance measures the correct harmonic, not only sampled phase.
    residual_hz = np.diff(x[:, 0]) * loop.fs / (2 * np.pi)
    valid = np.max(np.abs(vcontrol)) <= cfg["loop"]["control_voltage_deviation_limit_v"]
    okay = (np.abs(phase[1:]) < cfg["transient"]["phase_tolerance_rad"]) & (np.abs(residual_hz) < cfg["transient"]["frequency_tolerance_hz"])
    failures = np.flatnonzero(~okay)
    settled_index = int(failures[-1] + 2) if len(failures) else 1
    settled = valid and settled_index < n - 100
    return {"phase0_rad": phase0, "frequency_error_hz": frequency_error, "settled_correct_harmonic": settled,
            "settling_us": settled_index / loop.fs * 1e6 if settled else None,
            "max_sampled_control_deviation_v": float(np.max(np.abs(vcontrol))), "within_assumed_sampled_control_range": bool(valid),
            "last_phase_error_rad": float(phase[-1]), "last_frequency_error_hz": float(np.mean(residual_hz[-100:]))}, x


def retiming_case(cfg, point, duty, logic_delay_ps=None, skew_ps=0, seed_offset=0):
    p = cfg["retiming"]
    rng = np.random.default_rng(cfg["seed"] + point["k"] * 100 + seed_offset)
    count = p["events"]
    tvco = 1 / point["fvco_hz"]
    index = np.arange(count) * (point["m"] // 2)
    launch = index * tvco
    capture = launch + duty * tvco
    common = lambda t: np.sqrt(2) * p["common_timing_rms_fs"] * 1e-15 * np.sin(2 * np.pi * p["common_timing_test_frequency_hz"] * t)
    delay = p["logic_delay_ps"] if logic_delay_ps is None else logic_delay_ps
    data = launch + common(launch) + delay * 1e-12 + rng.normal(0, p["logic_jitter_ps"] * 1e-12, count)
    clock = capture + common(capture) + rng.normal(0, p["clock_buffer_jitter_fs"] * 1e-15, count)
    setup = clock - data - p["setup_ps"] * 1e-12
    hold = data[1:] - clock[:-1] - p["hold_ps"] * 1e-12
    edge_skew = (np.arange(count) % 2) * skew_ps * 1e-12
    output = clock + edge_skew + rng.normal(0, p["clkq_jitter_fs"] * 1e-15, count) + rng.normal(0, p["output_buffer_jitter_fs"] * 1e-15, count)
    tie = output - capture - edge_skew
    high = output[1::2] - output[0::2]
    period = output[2::2] - output[:-2:2]
    safe = np.all(setup > 0) and np.all(hold > 0)
    return {**point, "vco_duty": duty, "logic_delay_ps": delay, "rise_fall_skew_ps": skew_ps,
            "setup_min_ps": float(setup.min() * 1e12), "hold_min_ps": float(hold.min() * 1e12),
            "setup_violations": int(np.sum(setup <= 0)), "hold_violations": int(np.sum(hold <= 0)),
            "timing_valid": bool(safe), "divider_raw_tie_fs": float(np.std(data - launch - delay * 1e-12) * 1e15),
            "retimed_raw_tie_fs": float(np.std(tie) * 1e15) if safe else None,
            "retimer_added_raw_tie_fs": float(np.std(tie - common(capture)) * 1e15) if safe else None,
            "common_timing_gain": float(np.cov(tie, common(capture))[0, 1] / np.var(common(capture), ddof=1)) if safe else None,
            "mean_output_duty_percent": float(np.mean(high[:-1] / period) * 100) if safe else None}
