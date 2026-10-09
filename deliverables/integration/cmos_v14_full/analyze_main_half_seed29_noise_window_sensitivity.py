"""Check finite-window sensitivity without changing the preregistered metric."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
from noise_utils import cross

H=Path(__file__).resolve().parent
ROOT=H.parents[3]


def main():
    p=json.loads((H/'results/full_pll_main_half_seed29_pair_protocol.json').read_text())
    vp=H/'results/full_pll_main_half_seed29_pair_validation.json'
    v=json.loads(vp.read_text());assert v['high_offset_diagnostic_valid']
    edges=[]
    for c in p['cases']:
        f=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']/'waveforms.npz'
        with np.load(f) as z:e=cross(z['time'],z['out'],.6)
        edges.append(e[e>=p['measurement_start_s']][:p['edge_count']])
    r=edges[1]-edges[0];r-=r.mean();n=len(r)
    freq=np.fft.rfftfreq(n,1/p['output_hz'])
    selected=(freq>=p['band_hz'][0])&(freq<=p['band_hz'][1]);rows=[]
    for name,w in [('rectangular',np.ones(n)),('symmetric_hann',np.hanning(n))]:
        power=abs(np.fft.rfft(r*w))**2/(n*np.sum(w*w));power[1:-1]*=2
        rows.append(dict(window=name,band_rms_fs=float(np.sqrt(power[selected].sum())*1e15),
            noise_energy_normalization=float(np.mean(w*w)),enbw_bins=float(n*np.sum(w*w)/(np.sum(w)**2))))
    assert np.isclose(rows[0]['band_rms_fs'],v['diagnostic_band_rms_fs'],rtol=1e-12)
    out=dict(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,
        parent_validation_sha256=hashlib.sha256(vp.read_bytes()).hexdigest(),samples=n,band_hz=v['effective_band_hz'],
        endpoint_difference_ps=float((r[-1]-r[0])*1e12),methods=rows,full_pll_acceptance=False,
        limitations=['Window dependence includes finite-record weighting and leakage; it does not independently separate physical low-frequency noise from leakage.',
            'Hann uses sum(w^2) noise-energy normalization; no trend fit or arbitrary notches.',
            'Only longer records and multiple seeds can constrain this uncertainty; neither value is a 10kHz full-band result.',
            'Retain the preregistered rectangular result; never select a preferred lower value as acceptance.'])
    (H/'results/full_pll_main_half_seed29_noise_window_sensitivity.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
