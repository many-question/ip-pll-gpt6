"""Run all behavioral studies. Usage: python run.py --out <new output directory>."""
from __future__ import annotations

import argparse
import copy
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
from dataclasses import replace

import numpy as np
import scipy

from model import (synthesize, grid, noise_kernels, integrate_points, sampled_matrices,
                   continuous_open, hybrid_reference_transfer, local_transient, retiming_case, points)
from verify import verify


def dump(path, data):
    def convert(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False, default=convert) + "\n", encoding="utf-8", newline="\n")


def csvwrite(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    here = Path(__file__).resolve().parent
    cfg = json.loads((here / "config.json").read_text(encoding="utf-8"))
    dump(out / "input.json", cfg)
    loop = synthesize(cfg)
    f = grid(cfg)
    kernel = noise_kernels(loop, cfg, f)
    nominal = integrate_points(cfg, f, kernel, cfg["loop"]["crossover_hz"])
    csvwrite(out / "nominal_noise.csv", nominal)
    continuous = integrate_points(cfg, f, noise_kernels(loop, cfg, f, "continuous"), cfg["loop"]["crossover_hz"], "continuous")
    csvwrite(out / "continuous_comparison.csv", continuous)
    checks = verify(cfg, loop)
    # Independent quadrature-resolution convergence check including alias neighborhoods.
    fine_f = grid(cfg, multiplier=2)
    fine = integrate_points(cfg, fine_f, noise_kernels(loop, cfg, fine_f), cfg["loop"]["crossover_hz"])
    quadrature_error = float(max(abs(a["total_fs"] / b["total_fs"] - 1) for a, b in zip(nominal, fine)))
    checks["checks"].append({"name": "Double-density harmonic quadrature convergence", "observed": quadrature_error, "limit": .005, "passed": quadrature_error < .005})
    # Confirm reference contribution independence from frequency conversion at fixed integration window.
    ref_values = [r["reference_fs"] for r in nominal if r["window"] == "10k_to_10M"]
    checks["checks"].append({"name": "Reference time noise unchanged by ideal N/M scaling", "observed": float(np.ptp(ref_values)), "limit": 1e-10, "passed": np.ptp(ref_values) < 1e-10})
    checks["all_passed"] = all(row["passed"] for row in checks["checks"])
    dump(out / "validation.json", checks)
    print("Numerical validation:", checks["all_passed"], flush=True)

    designs, bandwidth_rows, stability_rows = [], [], []
    for fc in cfg["sweeps"]["crossover_hz"]:
        candidate = synthesize(cfg, fc)
        radius = float(max(abs(np.linalg.eigvals(sampled_matrices(candidate)[0]))))
        g = continuous_open(candidate, np.array([fc]))[0]
        cap_pf = (candidate.c1 + candidate.c2) * 1e12
        cap_area = (candidate.c1 + candidate.c2) * 1e9 * cfg["allocation"]["capacitor_area_overhead_factor"]
        design = {"design_crossover_hz": fc, "r_ohm": candidate.r, "c1_pf": candidate.c1 * 1e12, "c2_pf": candidate.c2 * 1e12,
                  "ct_phase_margin_deg": 180 + float(np.angle(g, deg=True)), "sampled_radius": radius,
                  "stable": radius < 1, "filter_cap_area_mm2_at_1ff_um2": cap_area,
                  "required_density_ff_um2_to_fit_filter_budget": cap_area / cfg["allocation"]["area_mm2"]["filter"]}
        for density in cfg["sweeps"]["capacitor_density_ff_per_um2"]:
            design[f"filter_area_mm2_density_{density}"] = cap_area / density
        if radius < 1:
            rows = integrate_points(cfg, f, noise_kernels(candidate, cfg, f), fc)
            bandwidth_rows.extend(rows)
            design["worst_fixed_fs"] = max(r["total_fs"] for r in rows if r["window"] == "10k_to_10M")
            design["worst_wide_fs"] = max(r["total_fs"] for r in rows if r["window"] == "10k_to_fout_over_2")
        else:
            design["worst_fixed_fs"] = design["worst_wide_fs"] = None
        designs.append(design)
        for gain in cfg["sweeps"]["gain_scale"]:
            for delay in cfg["sweeps"]["extra_delay_cycles"]:
                changed = replace(candidate, kpd=candidate.kpd * gain, latency=delay)
                rho = float(max(abs(np.linalg.eigvals(sampled_matrices(changed)[0]))))
                stability_rows.append({"design_crossover_hz": fc, "combined_kpd_kv_gain_scale_fixed_RC": gain,
                                       "extra_sample_delay": delay, "sampled_radius": rho, "stable": rho < 1})
    csvwrite(out / "loop_designs.csv", designs)
    csvwrite(out / "bandwidth_noise.csv", bandwidth_rows)
    csvwrite(out / "stability_sweep.csv", stability_rows)

    # PSD linearity allows independent source scaling without rerunning the loop.
    scenarios = []
    white_cfg = copy.deepcopy(cfg)
    white_cfg["noise"]["vco_close_in_l1mhz_dbc_hz"] = -1000
    white_kernel = noise_kernels(loop, white_cfg, f)
    white_only = integrate_points(cfg, f, white_kernel, cfg["loop"]["crossover_hz"])
    for l1 in cfg["sweeps"]["vco_l1mhz_dbc_hz"]:
        for ref in cfg["sweeps"]["reference_asd_as_per_sqrt_hz"]:
            for row, floor in zip(nominal, white_only):
                scaled = row.copy()
                vco_var = floor["vco_fs"] ** 2 + (row["vco_fs"] ** 2 - floor["vco_fs"] ** 2) * 10 ** ((l1 - cfg["noise"]["vco_close_in_l1mhz_dbc_hz"]) / 10)
                ref_var = row["reference_fs"] ** 2 * (ref / cfg["noise"]["reference_time_asd_as_per_sqrt_hz"]) ** 2
                scaled.update({"vco_l1mhz_dbc_hz": l1, "reference_asd_as_sqrt_hz": ref, "vco_fs": np.sqrt(vco_var), "reference_fs": np.sqrt(ref_var),
                               "total_fs": np.sqrt(row["total_fs"] ** 2 - row["vco_fs"] ** 2 - row["reference_fs"] ** 2 + vco_var + ref_var)})
                scaled["below_200fs_in_hypothesis"] = scaled["total_fs"] < 200
                scenarios.append(scaled)
    csvwrite(out / "source_sensitivity.csv", scenarios)
    constraints = []
    for row, floor in zip(nominal, white_only):
        budget = cfg["allocation"]["jitter_budget_fs"]
        remaining_vco_variance = budget["vco"] ** 2 - floor["vco_fs"] ** 2
        scale_limit = remaining_vco_variance / (row["vco_fs"] ** 2 - floor["vco_fs"] ** 2)
        constraints.append({"k": row["k"], "m": row["m"], "window": row["window"],
                            "vco_close_in_L1MHz_boundary_dbc_hz": cfg["noise"]["vco_close_in_l1mhz_dbc_hz"] + 10 * np.log10(scale_limit) if scale_limit > 0 else None,
                            "reference_asd_boundary_as_sqrt_hz": cfg["noise"]["reference_time_asd_as_per_sqrt_hz"] * budget["reference"] / row["reference_fs"],
                            "sampler_C_each_boundary_ff": cfg["noise"]["sampling_capacitance_each_f"] * 1e15 * (row["sampler_fs"] / budget["sampler"]) ** 2,
                            "cp_period_average_asd_boundary_pa_sqrt_hz": cfg["noise"]["cp_period_average_current_asd_a_per_sqrt_hz"] * 1e12 * budget["charge_pump"] / row["charge_pump_fs"],
                            "retimer_time_asd_boundary_as_sqrt_hz": budget["retimer"] * 1e3 / np.sqrt(row["high_hz"] - cfg["integration"]["low_hz"])})
    csvwrite(out / "block_noise_boundaries.csv", constraints)
    thermal = []
    for temperature in cfg["sweeps"]["temperature_c"]:
        for row in nominal:
            factor = (temperature + 273.15) / (cfg["loop"]["temperature_c"] + 273.15)
            thermal.append({"k": row["k"], "window": row["window"], "temperature_c": temperature,
                            "thermal_only_total_fs": np.sqrt(row["total_fs"] ** 2 + (factor - 1) * (row["sampler_fs"] ** 2 + row["filter_resistor_fs"] ** 2)),
                            "is_PVT_verification": False})
    csvwrite(out / "thermal_only_sensitivity.csv", thermal)

    transient_rows, selected_traces = [], []
    for phase in cfg["transient"]["phase_initial_rad"]:
        for delta in cfg["transient"]["frequency_error_hz"]:
            result, trajectory = local_transient(loop, cfg, phase, delta)
            transient_rows.append(result)
            if phase == .5 and delta in (1e6, 4e6):
                selected_traces.append((delta, trajectory))
                csvwrite(out / f"transient_{int(delta)}Hz.csv", [{"time_us": i / loop.fs * 1e6, "unwrapped_phase_rad": state[0], "control_deviation_v": state[1] * loop.fs / loop.kv} for i, state in enumerate(trajectory)])
    csvwrite(out / "local_acquisition.csv", transient_rows)
    retiming = []
    for point in points(cfg):
        for duty in cfg["retiming"]["vco_duty_sweep"]:
            retiming.append(retiming_case(cfg, point, duty))
        retiming.append(retiming_case(cfg, point, .5, skew_ps=cfg["retiming"]["rise_fall_skew_ps"]))
        retiming.append(retiming_case(cfg, point, .4, logic_delay_ps=cfg["retiming"]["stress_logic_delay_ps"]))
    csvwrite(out / "retiming.csv", retiming)

    allocation = cfg["allocation"]
    summary = {
        "model": cfg["model_version"], "time": datetime.datetime.now().astimezone().isoformat(),
        "evidence": "behavioral_sim_with_hypothetical_parameters_not_circuit_performance",
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "validation_all_passed": checks["all_passed"], "nominal_loop": loop.__dict__,
        "nominal_worst_fixed": max((r for r in nominal if r["window"] == "10k_to_10M"), key=lambda r: r["total_fs"]),
        "nominal_worst_wide": max((r for r in nominal if r["window"] == "10k_to_fout_over_2"), key=lambda r: r["total_fs"]),
        "jitter_allocated_rss_fs": float(np.linalg.norm(list(allocation["jitter_budget_fs"].values()))),
        "power_allocated_mw": sum(allocation["power_mw"].values()), "power_margin_mw": 4 - sum(allocation["power_mw"].values()),
        "area_allocated_mm2": sum(allocation["area_mm2"].values()), "area_margin_mm2": .3 - sum(allocation["area_mm2"].values()),
        "sampled_unstable_scenarios": sum(not r["stable"] for r in stability_rows), "sampled_scenarios": len(stability_rows),
        "local_capture_successes": sum(r["settled_correct_harmonic"] for r in transient_rows), "local_capture_cases": len(transient_rows),
        "retiming_valid_scenarios": sum(r["timing_valid"] for r in retiming), "retiming_scenarios": len(retiming),
        "limitations": ["Circuit/noise/pulse/timing parameters are hypotheses; no PDK validation.", "No deterministic spur model or autonomous FLL/cap-bank algorithm.",
                        "Reference and CP input PSDs are effective post-sampling/baseband values; unknown external alias contributions are not automatically covered.",
                        "Continuous VCO and resistor-noise aliases are summed with a 2 GHz source cutoff and 10 Hz low-frequency regularization.",
                        "Noise spectrum is cycle-averaged continuous-time output; divider edge aliasing and cyclostationary edge selection are not fully modeled.",
                        "Temperature sweep changes kT only, not PVT gains/frequency/power.", "Retiming raw TIE is a separate timing experiment, not the band-integrated PLL jitter result."]
    }
    dump(out / "summary.json", summary)
    os.environ["MPLCONFIGDIR"] = str(out / "matplotlib_cache")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": .25, "savefig.dpi": 160})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for method, data in [("Sampled pulse", nominal), ("Continuous approximation", continuous)]:
        for window, style in [("10k_to_10M", "-"), ("10k_to_fout_over_2", "--")]:
            values = [r for r in data if r["window"] == window]
            axes[0].plot([r["fout_hz"] / 1e6 for r in values], [r["total_fs"] for r in values], style, label=method + ": " + ("10 MHz" if style == "-" else "fout/2"))
    axes[0].axhline(200, color="black", ls=":", label="Requirement")
    axes[0].set(xlabel="Output frequency (MHz)", ylabel="RMS random jitter (fs)", title="Hypothetical noise inputs; no spur")
    axes[0].legend(fontsize=7)
    worst = summary["nominal_worst_wide"]
    keys = list(allocation["jitter_budget_fs"])
    axes[1].barh(keys, [worst[key + "_fs"] for key in keys], color="#187b91")
    axes[1].set(xlabel="Contribution (fs RMS)", title=f"Worst wide-window point: {worst['fout_hz']/1e6:.0f} MHz")
    fig.tight_layout()
    fig.savefig(out / "noise_summary.png")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    stable = [r for r in designs if r["stable"]]
    axes[0].plot([r["design_crossover_hz"] / 1e6 for r in stable], [r["worst_wide_fs"] for r in stable], "o-")
    axes[0].axhline(200, color="black", ls=":")
    axes[0].set(xlabel="Synthesized continuous crossover (MHz)", ylabel="Worst 33-point RMS jitter (fs)", title="Pulse-aware noise / bandwidth tradeoff")
    axes[1].loglog([r["design_crossover_hz"] / 1e6 for r in designs], [r["filter_cap_area_mm2_at_1ff_um2"] for r in designs], "o-")
    axes[1].axhline(.04, color="black", ls=":", label="Proposed filter allocation")
    axes[1].set(xlabel="Synthesized continuous crossover (MHz)", ylabel="Filter capacitor area (mm2)", title="1 fF/um2 + 20% overhead assumption")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "bandwidth_area.png")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for delta, trajectory in selected_traces:
        t = np.arange(len(trajectory)) / loop.fs * 1e6
        axes[0].plot(t, np.angle(np.exp(1j * trajectory[:, 0])), label=f"Initial frequency error {delta/1e6:.0f} MHz")
        axes[1].plot(t, trajectory[:, 1] * loop.fs / loop.kv, label=f"{delta/1e6:.0f} MHz")
    axes[0].set(xlim=(0, 25), xlabel="Time (us)", ylabel="Wrapped phase error (rad)", title="Main-loop local acquisition; FLL absent")
    axes[1].set(xlim=(0, 25), xlabel="Time (us)", ylabel="Sampled control deviation (V)")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "local_acquisition.png")
    plt.close(fig)
    manifest = {"source_files": {}, "result_files": {}}
    for file in sorted(here.glob("*.py")) + [here / "config.json"]:
        manifest["source_files"][file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    for file in sorted(out.glob("*")):
        if file.is_file():
            manifest["result_files"][file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    dump(out / "manifest.json", manifest)
    print(json.dumps({"out": str(out), "validation_passed": checks["all_passed"], "worst_fixed_fs": summary["nominal_worst_fixed"]["total_fs"],
                      "worst_wide_fs": summary["nominal_worst_wide"]["total_fs"], "unstable_cases": summary["sampled_unstable_scenarios"]}, indent=2), flush=True)
    if not checks["all_passed"]:
        raise SystemExit("Numerical validation failed; see validation.json")


if __name__ == "__main__":
    main()
