"""Finite edge-count FLL and nonlinear sampled SSPLL, candidate B.

No target-frequency shortcut: the FLL observes integer VCO edge counts only.
Coarse reset uses an ideal, explicitly modeled filter precharge; phase is retained.
"""
from pathlib import Path
import sys
import json
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavioral_v1'))
from model import synthesize, sampled_matrices, points, partial_pulse, plant
from scipy.linalg import expm

CFG_PATH = Path(__file__).resolve().parents[1] / 'behavioral_v1/results/candidate/candidate_B.json'
CFG = json.loads(CFG_PATH.read_text(encoding='utf-8'))
FS = 24e6
KV = 20e6
FH = 4.00e9
FL = 2.64e9
VMID, VLOW, VHIGH = .6, .2, 1.0
WINDOW = 32
SETTLE = 2


def bank_hz(code, scale=1.0):
    """256 equal-C codes; frequency guard band is a research assumption."""
    return scale * FH / np.sqrt(1 + code / 255 * ((FH / FL) ** 2 - 1))


def run_case(k, initial_code=127, phase0=.7, bank_scale=1., samples=1200,
             forced_target=None, disturbance_hz=0., disturbance_cycle=None,
             substeps=1):
    point = next(p for p in points(CFG) if p['k'] == k)
    target = point['fvco_hz'] if forced_target is None else forced_target
    nratio = target / FS
    loop = synthesize(CFG)
    _, _, _, e, pulse = sampled_matrices(loop)
    a, _ = plant(loop)
    # State is phase error and two normalized filter voltages relative to .6 V.
    x = np.array([phase0, 0., 0.])
    scalev = 2 * np.pi * KV / FS
    code, lo, hi = initial_code, 0, 255
    bestcode, besterr = code, float('inf')
    state, age, trials, handoff = 'search', 0, 0, None
    count_start = 0
    preset = VMID
    freq_offset = 0.
    searches = 1
    watchdog_start = None
    trace = []
    rails = 0
    # Exact subinterval matrices also give intracycle rail observations.
    taus = np.unique(np.r_[np.linspace(0, 1, substeps + 1), loop.delay, loop.delay + loop.duty])
    maps = [(float(t), expm(a * t), partial_pulse(loop, t)) for t in taus[1:]]
    for i in range(samples):
        if disturbance_cycle is not None and i == disturbance_cycle:
            freq_offset = disturbance_hz
        absolute_cycles = i * nratio + x[0] / (2 * np.pi)
        edges = int(np.floor(absolute_cycles))
        fcenter = bank_hz(code, bank_scale) + freq_offset
        phase = float(np.angle(np.exp(1j * x[0])))
        if state == 'search':
            if age == SETTLE:
                count_start = edges
            if age == SETTLE + WINDOW:
                err = (edges - count_start) * FS / WINDOW - target
                trials += 1
                if abs(err) < abs(besterr):
                    besterr, bestcode = err, code
                if err > 0:
                    lo = code + 1
                else:
                    hi = code - 1
                if lo > hi or trials >= 9 or abs(err) < FS / WINDOW / 2:
                    code = bestcode
                    preset = float(np.clip(VMID - besterr / KV, VLOW + .02, VHIGH - .02))
                    state, age = 'precharge', -1
                else:
                    code, age = (lo + hi) // 2, -1
                fcenter = bank_hz(code, bank_scale) + freq_offset
            # VA updates bank and precharge voltage at the same reference edge.
            x[1:] = (preset - VMID) * scalev if state == 'precharge' else 0
        elif state == 'precharge':
            x[1:] = (preset - VMID) * scalev
            if age >= SETTLE:
                state, age, handoff = 'track', 0, i
        elif state == 'track':
            # A 32-reference monitor window every 256 cycles; counter is gated
            # outside it. This is a functional policy, not a power estimate.
            if age % 256 == 192:
                watchdog_start = edges
            if age % 256 == 224 and watchdog_start is not None:
                err = (edges - watchdog_start) * FS / WINDOW - target
                if abs(err) > 3e6:
                    state, age, lo, hi, trials = 'search', -1, 0, 255, 0
                    besterr, bestcode, preset = float('inf'), code, VMID
                    searches += 1
                    x[1:] = 0
        v = VMID + x[1] / scalev
        trace.append((i / FS, code, {'search':0,'precharge':1,'track':2}[state],
                      phase, v, VMID + x[2] / scalev, fcenter + KV * np.clip(v-VMID,-.4,.4), searches))
        advance = 2 * np.pi * (fcenter - target) / FS
        if state != 'track':
            x[0] += advance + x[1]
        else:
            drive = -np.sin(x[0])
            interior = [ee @ x + bp * drive + np.array([advance * t,0,0]) for t,ee,bp in maps]
            maximum = max(abs(y[1] / scalev) for y in interior)
            if maximum > .4:
                # Rail violations are explicit invalid cases, never silently
                # accepted using an unclipped linear oscillator.
                rails += 1
            x = interior[-1]
        age += 1
    trace = np.array(trace)
    final_freq = np.mean(trace[-100:,6]) - target
    okay = (np.abs(trace[:,3]) < .01) & (np.abs(trace[:,6] - target) < 1e3) & (trace[:,2] == 2)
    fail = np.flatnonzero(~okay)
    settled_index = int(fail[-1] + 1) if len(fail) else 0
    settled = settled_index < samples - 100 and rails == 0
    return {**point, 'initial_code':initial_code,'phase0_rad':phase0,'bank_scale':bank_scale,
            'target_hz':target,'selected_code':int(code),'searches':searches,'trials_last_search':trials,
            'handoff_us': None if handoff is None else handoff/FS*1e6,
            'settled':bool(settled),'settling_us':settled_index/FS*1e6 if settled else None,
            'final_error_hz':float(final_freq),'final_phase_rad':float(trace[-1,3]),
            'control_min_v':float(trace[:,4].min()),'control_max_v':float(trace[:,4].max()),
            'rail_violation_cycles':rails}, trace


if __name__ == '__main__':
    print(json.dumps(run_case(41)[0], indent=2))
