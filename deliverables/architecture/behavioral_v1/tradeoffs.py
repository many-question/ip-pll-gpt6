"""Follow-up experiment: jointly vary Kvco, detector gain, and sampler capacitance.

Keeps negative budget results. CP noise scales as sqrt(detector gain), an explicit
fixed-topology thermal-noise hypothesis, not a circuit extraction.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from dataclasses import replace

import numpy as np

from model import synthesize, grid, noise_kernels, integrate_points, sampled_matrices, local_transient
from run import dump, csvwrite
from verify import verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    here = Path(__file__).resolve().parent
    cfg = json.loads((here / "config.json").read_text(encoding="utf-8"))
    f = grid(cfg)
    rows = []
    for kv in (10e6, 20e6, 40e6, 80e6):
        for gain_factor in (.5, 1., 2., 4.):
            changed = copy.deepcopy(cfg)
            changed["loop"]["kvco_hz_per_v"] = kv
            changed["loop"]["kpd_average_a_per_rad"] *= gain_factor
            changed["noise"]["cp_period_average_current_asd_a_per_sqrt_hz"] *= np.sqrt(gain_factor)
            lp = synthesize(changed)
            noise = integrate_points(changed, f, noise_kernels(lp, changed, f), changed["loop"]["crossover_hz"])
            worst = max((r for r in noise if r["window"] == "10k_to_fout_over_2"), key=lambda r: r["total_fs"])
            fine_span = 2 * cfg["loop"]["control_voltage_deviation_limit_v"] * kv
            max_step = .8 * fine_span
            codes = int(np.ceil((3.936e9 - 2.688e9) / max_step)) + 1
            cap_ratio = (3.936e9 / 2.688e9) ** 2
            maximum_cap_step_relative = (3.936e9 / (3.936e9 - max_step)) ** 2 - 1
            uniform_cap_codes = int(np.ceil((cap_ratio - 1) / maximum_cap_step_relative)) + 1
            rows.append({"kvco_mhz_v": kv / 1e6, "kpd_uA_rad": lp.kpd * 1e6, "cp_noise_scaling": "sqrt(Kpd/Kpd0)",
                         "c1_pf": lp.c1 * 1e12, "c2_pf": lp.c2 * 1e12, "r_ohm": lp.r,
                         "filter_cap_area_mm2_at_1ff_um2": (lp.c1 + lp.c2) * 1e9 * cfg["allocation"]["capacitor_area_overhead_factor"],
                         "worst_wide_fs": worst["total_fs"], "filter_resistor_fs": worst["filter_resistor_fs"],
                         "charge_pump_fs": worst["charge_pump_fs"], "sampler_fs": worst["sampler_fs"],
                         "fine_tuning_span_mhz_assumed_0p8V": fine_span / 1e6,
                         "maximum_coarse_step_mhz_20pct_overlap": max_step / 1e6,
                         "minimum_uniform_frequency_code_count_no_PVT": codes, "uniform_frequency_binary_bits_no_PVT": int(np.ceil(np.log2(codes))),
                         "minimum_uniform_capacitance_code_count_no_PVT": uniform_cap_codes,
                         "uniform_capacitance_binary_bits_no_PVT": int(np.ceil(np.log2(uniform_cap_codes)))})
    csvwrite(out / "kvco_kpd_tradeoff.csv", rows)
    # A candidate within the existing nominal filter-area allocation, selected for
    # lower noise without changing the nominal RC or loop bandwidth.
    candidate = copy.deepcopy(cfg)
    candidate["loop"]["kvco_hz_per_v"] = 20e6
    candidate["loop"]["kpd_average_a_per_rad"] = 2.4e-6
    candidate["noise"]["sampling_capacitance_each_f"] = 40e-15
    candidate["noise"]["cp_period_average_current_asd_a_per_sqrt_hz"] = 0.5e-12
    candidate["parameter_status"] += "; candidate B is a work proposal, not a frozen circuit"
    dump(out / "candidate_B.json", candidate)
    lp = synthesize(candidate)
    kernels = noise_kernels(lp, candidate, f)
    noise = integrate_points(candidate, f, kernels, candidate["loop"]["crossover_hz"])
    csvwrite(out / "candidate_B_noise.csv", noise)
    validation = verify(candidate, lp)
    dump(out / "candidate_B_validation.json", validation)
    capture = [local_transient(lp, candidate, phase, error)[0] for phase in candidate["transient"]["phase_initial_rad"] for error in candidate["transient"]["frequency_error_hz"]]
    csvwrite(out / "candidate_B_local_acquisition.csv", capture)
    worst = max((r for r in noise if r["window"] == "10k_to_fout_over_2"), key=lambda r: r["total_fs"])
    block_limits = []
    for key, budget in candidate["allocation"]["jitter_budget_fs"].items():
        maximum = max(row[key + "_fs"] for row in noise if row["window"] == "10k_to_fout_over_2")
        block_limits.append({"block": key, "provisional_budget_fs": budget, "maximum_simulated_fs": maximum,
                             "all_wide_windows_within_block_budget": maximum <= budget})
    csvwrite(out / "candidate_B_block_allocation_check.csv", block_limits)
    revised_budget = {"reference": 65, "reference_buffer": 45, "sampler": 30, "charge_pump": 25,
                      "filter_resistor": 30, "vco": 135, "retimer": 45, "output_buffer": 45}
    dump(out / "working_allocation_B.json", {"status": "proposal_not_frozen", "jitter_fs": revised_budget,
                                            "rss_fs": float(np.linalg.norm(list(revised_budget.values()))),
                                            "reason": "Retain the initial allocation failure; move unused CP budget to VCO and wide-band output floor."})

    robustness = []
    for kv_scale in (.5, 1, 2):
        for kp_scale in (.5, 1, 2):
            for latency in (0, 1):
                test_loop = replace(lp, kv=lp.kv * kv_scale, kpd=lp.kpd * kp_scale, latency=latency)
                rho = float(max(abs(np.linalg.eigvals(sampled_matrices(test_loop)[0]))))
                test_cfg = copy.deepcopy(candidate)
                test_cfg["noise"]["cp_period_average_current_asd_a_per_sqrt_hz"] *= np.sqrt(kp_scale)
                worst_fs = None
                if rho < 1:
                    values = integrate_points(test_cfg, f, noise_kernels(test_loop, test_cfg, f), candidate["loop"]["crossover_hz"])
                    worst_fs = max(r["total_fs"] for r in values if r["window"] == "10k_to_fout_over_2")
                robustness.append({"kvco_gain_scale": kv_scale, "kpd_gain_scale": kp_scale, "extra_sample_delay": latency,
                                   "fixed_nominal_RC": True, "sampled_radius": rho, "stable": rho < 1,
                                   "worst_wide_fs": worst_fs, "is_PVT_simulation": False})
    csvwrite(out / "candidate_B_gain_delay_sensitivity.csv", robustness)

    # This integrates all pre-divider noise up to the explicit analog cutoff; it
    # is a sensitivity screen, not an exact synchronous edge-aliasing model.
    broad_f = grid(candidate, high=candidate["noise"]["analog_noise_cutoff_hz"])
    broad = noise_kernels(lp, candidate, broad_f)
    broad_variance = {key: float(np.trapezoid(value, broad_f)) for key, value in broad.items() if key not in ("retimer", "output_buffer")}
    wide_sensitivity = []
    for row in noise:
        if row["window"] != "10k_to_fout_over_2":
            continue
        total = row["retimer_fs"] ** 2 + row["output_buffer_fs"] ** 2
        for key, variance in broad_variance.items():
            scale = (2 * np.pi * row["fvco_hz"]) ** 2 if key in ("sampler", "charge_pump", "filter_resistor", "vco") else 1
            total += variance / scale * 1e30
        wide_sensitivity.append({"k": row["k"], "fout_hz": row["fout_hz"], "reported_window_fs": row["total_fs"],
                                 "full_predivider_2GHz_variance_screen_fs": np.sqrt(total), "exact_edge_aliasing_model": False})
    csvwrite(out / "candidate_B_high_frequency_tail.csv", wide_sensitivity)

    cutoff_sensitivity = []
    for cutoff in (1e9, 2e9, 4e9):
        trial = copy.deepcopy(candidate)
        trial["noise"]["analog_noise_cutoff_hz"] = cutoff
        values = integrate_points(trial, f, noise_kernels(lp, trial, f), trial["loop"]["crossover_hz"])
        cutoff_sensitivity.append({"source_cutoff_hz": cutoff, "worst_wide_fs": max(r["total_fs"] for r in values if r["window"] == "10k_to_fout_over_2")})
    csvwrite(out / "source_cutoff_sensitivity.csv", cutoff_sensitivity)

    summary = {"selected_candidate": "B (proposal)", "reason": "Kvco /4 and Kpd x4 keep RC and dynamics unchanged; filter resistor time jitter /4; CP ASD x2 assumption; sampler C x2.",
               "nominal_loop": lp.__dict__, "worst_wide": worst,
               "worst_fixed_fs": max(r["total_fs"] for r in noise if r["window"] == "10k_to_10M"),
               "worst_full_predivider_variance_screen_fs": max(r["full_predivider_2GHz_variance_screen_fs"] for r in wide_sensitivity),
               "validation_all_passed": validation["all_passed"],
               "working_allocation_B_rss_fs": float(np.linalg.norm(list(revised_budget.values()))),
               "gain_delay_scenarios": len(robustness), "gain_delay_unstable_cases": sum(not r["stable"] for r in robustness),
               "gain_delay_stable_cases_above_200fs": sum(r["stable"] and r["worst_wide_fs"] >= 200 for r in robustness),
               "provisional_blocks_above_allocation": [r["block"] for r in block_limits if not r["all_wide_windows_within_block_budget"]],
               "not_demonstrated": ["PDK-realizable gain/noise/power/area", "Fine tuning linearity and PVT overlap", "Synchronous divider cyclostationary edge aliasing", "Full FLL startup", "Spur"]}
    dump(out / "summary.json", summary)
    os.environ["MPLCONFIGDIR"] = str(out / "matplotlib_cache")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    baseline_loop = synthesize(cfg)
    baseline = integrate_points(cfg, f, noise_kernels(baseline_loop, cfg, f), cfg["loop"]["crossover_hz"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for label, data, color in [("Initial A", baseline, "#cc6336"), ("Candidate B", noise, "#187b91")]:
        for window, style in [("10k_to_10M", "--"), ("10k_to_fout_over_2", "-")]:
            values = [r for r in data if r["window"] == window]
            axes[0].plot([r["fout_hz"] / 1e6 for r in values], [r["total_fs"] for r in values], ls=style, color=color,
                         label=label + (": 10 MHz" if style == "--" else ": fout/2"))
    axes[0].axhline(200, color="black", ls=":", label="Requirement")
    axes[0].set(xlabel="Output frequency (MHz)", ylabel="RMS random jitter (fs)", title="Hypothetical inputs; no circuit data or spur")
    axes[0].legend(fontsize=8)
    old_worst = max((r for r in baseline if r["window"] == "10k_to_fout_over_2"), key=lambda r: r["total_fs"])
    keys = list(revised_budget)
    index = np.arange(len(keys))
    axes[1].barh(index - .18, [old_worst[k + "_fs"] for k in keys], height=.34, label="Initial A", color="#cc6336")
    axes[1].barh(index + .18, [worst[k + "_fs"] for k in keys], height=.34, label="Candidate B", color="#187b91")
    axes[1].set(yticks=index, yticklabels=keys, xlabel="Contribution (fs RMS)", title="672 MHz output / 2.688 GHz VCO")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
        ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out / "candidate_comparison.png", dpi=170)
    plt.close(fig)
    manifest = {"source_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in list(here.glob("*.py")) + [here / "config.json"]},
                "result_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}}
    dump(out / "manifest.json", manifest)
    print((out / "summary.json").read_text(encoding="utf-8"), flush=True)
    if not validation["all_passed"]:
        raise SystemExit("Candidate validation failed")


if __name__ == "__main__":
    main()
