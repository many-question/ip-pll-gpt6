"""Reproducible algebraic screen; Python 3.10+, standard library only.

Run from any working directory: python <path>/calculate.py
All numeric scenarios are targets or hypotheses, never simulated PLL performance.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def write_csv(name, rows):
    with (HERE / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    hyp = cfg["hypotheses"]
    rows = []
    for k in range(cfg["k_min"], cfg["k_max"] + 1):
        matching = [g for g in cfg["frequency_groups"] if g["k_min"] <= k <= g["k_max"]]
        assert len(matching) == 1, f"Missing or overlapping group for K={k}"
        m = matching[0]["m"]
        fout = k * cfg["reference_hz"]
        fvco = m * fout
        assert m % 2 == 0 and m in (4, 6, 8, 10, 12, 14)
        assert cfg["vco_min_hz"] <= fvco <= cfg["vco_max_hz"]
        # Each output half-period spans M/2 identical VCO cycles in an ideal counter.
        assert math.isclose((m // 2) / fvco, 0.5 / fout)
        rows.append({"k": k, "m": m, "n": k * m, "fout_hz": fout,
                     "fvco_hz": fvco, "ideal_half_period_s": 0.5 / fout,
                     "ideal_phase_noise_reduction_db": 20 * math.log10(m)})
    assert len(rows) == 33
    assert all(b["fout_hz"] - a["fout_hz"] == cfg["reference_hz"] for a, b in zip(rows, rows[1:]))

    fmin, fmax = min(r["fvco_hz"] for r in rows), max(r["fvco_hz"] for r in rows)
    tank = []
    for inductance_nh in hyp["tank_inductance_sweep_nh"]:
        inductance = inductance_nh * 1e-9
        tank.append({"hypothetical_effective_L_nh": inductance_nh,
                     "Ctotal_at_fmax_pf": 1e12 / ((2 * math.pi * fmax) ** 2 * inductance),
                     "Ctotal_at_fmin_pf": 1e12 / ((2 * math.pi * fmin) ** 2 * inductance)})

    noise = []
    # These are constant mean-equivalent SSB levels using the WHOLE jitter budget.
    # They are not per-offset masks and not generated or measured spectra.
    for fout in (rows[0]["fout_hz"], rows[-1]["fout_hz"]):
        for high in (hyp["integration_fixed_high_hz"], fout / 2):
            low = hyp["integration_low_hz"]
            assert high > low
            integral = (2 * math.pi * fout * cfg["jitter_limit_s"]) ** 2 / 2
            noise.append({"fout_hz": fout, "integration_low_hz": low,
                          "integration_high_hz": high, "SSB_integrated_ratio_boundary": integral,
                          "mean_equivalent_SSB_boundary_dbc_hz": 10 * math.log10(integral / (high - low))})

    budgets = []
    for ref_fs in hyp["closed_loop_reference_contribution_sweep_fs"]:
        for chain_fs in hyp["output_chain_contribution_sweep_fs"]:
            remaining = (cfg["jitter_limit_s"] * 1e15) ** 2 - ref_fs ** 2 - chain_fs ** 2
            budgets.append({"closed_loop_reference_fs": ref_fs, "output_chain_fs": chain_fs,
                            "remaining_internal_rss_boundary_fs": math.sqrt(remaining) if remaining > 0 else None,
                            "positive_variance_margin": remaining > 0})

    # Algebraic cross-check: identical time error before/after ideal multiplication/division.
    arbitrary_time_error = 123e-15
    division_error = 0.0
    reference_error = 0.0
    for row in rows:
        input_phase = 2 * math.pi * row["fvco_hz"] * arbitrary_time_error
        output_time = (input_phase / row["m"]) / (2 * math.pi * row["fout_hz"])
        division_error = max(division_error, abs(output_time - arbitrary_time_error))
        reference_phase = 2 * math.pi * cfg["reference_hz"] * arbitrary_time_error
        output_ref_time = (reference_phase * row["n"] / row["m"]) / (2 * math.pi * row["fout_hz"])
        reference_error = max(reference_error, abs(output_ref_time - arbitrary_time_error))
    assert division_error < 1e-26 and reference_error < 1e-26

    summary = {
        "evidence": "estimate",
        "performance_simulated": False,
        "frequency_plan": {"count": len(rows), "fout_min_hz": rows[0]["fout_hz"],
                           "fout_max_hz": rows[-1]["fout_hz"], "fvco_min_hz": fmin, "fvco_max_hz": fmax,
                           "n_min": min(r["n"] for r in rows), "n_max": max(r["n"] for r in rows)},
        "tank": {"frequency_ratio": fmax / fmin, "Ctotal_ratio_fixed_L": (fmax / fmin) ** 2,
                 "span_over_mid_frequency": 2 * (fmax - fmin) / (fmax + fmin), "pvt_margin_included": False},
        "supply_current_limit_a": cfg["power_limit_w"] / cfg["supply_v"],
        "PLL_FOM_boundary_dB": 10 * math.log10(cfg["jitter_limit_s"] ** 2 * cfg["power_limit_w"] / 1e-3),
        "square_area_side_um": math.sqrt(cfg["area_limit_mm2"]) * 1000,
        "PM_spur_equivalent_rms_s_at_output": {
            str(fout): math.sqrt(2) * 10 ** (cfg["spur_limit_dbc"] / 20) / (2 * math.pi * fout)
            for fout in (rows[0]["fout_hz"], rows[-1]["fout_hz"])
        },
        "checks": {"frequency_points_checked": len(rows), "ideal_division_max_time_error_s": division_error,
                   "unity_closed_loop_reference_transfer_max_time_error_s": reference_error},
        "limits": ["No transistor, PDK, noise spectrum, sampled loop, startup, load, PVT, or layout model.",
                   "Integration bounds and swept inputs are unconfirmed hypotheses.",
                   "RSS requires uncorrelated contributions integrated over the same band; reference values are AFTER loop filtering.",
                   "Phase/time identities assume ideal noiseless scaling at the same offset frequencies, with no aliasing.",
                   "The PM spur conversion is for a symmetric pair of small pure phase modulation sidebands; AM is excluded.",
                   "All limits are equality boundaries; strict less-than specifications require additional margin."]
    }
    write_csv("frequency_plan.csv", rows)
    write_csv("tank_sweep.csv", tank)
    write_csv("equivalent_noise_limits.csv", noise)
    write_csv("jitter_budget_sensitivity.csv", budgets)
    (HERE / "results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    files = [p for p in sorted(HERE.iterdir()) if p.suffix in (".json", ".csv", ".py") and p.name != "manifest.json"]
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
