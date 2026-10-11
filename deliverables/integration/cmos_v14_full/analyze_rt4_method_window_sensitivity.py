"""Audit finite-window dependence of both method records without replacing the primary metric."""
from pathlib import Path
import datetime,json
import numpy as np
from audit_rt4_half_seed29_noise_recovery import sha
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]


def main():
    rows=[]
    for name in ['full_pll_rt4_quarter_pair_protocol.json','full_pll_rt4_gear_quarter_pair_protocol.json']:
        pp=H/'results'/name;p=json.loads(pp.read_text());vp=pp.with_name(name.replace('_protocol.json','_validation.json'));v=json.loads(vp.read_text())
        assert v['high_offset_diagnostic_valid'] and v['protocol_sha256']==sha(pp)
        edges=[];sources=[]
        for c,vc in zip(p['cases'],v['cases']):
            d=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case'];rp=d/'result.json';r=json.loads(rp.read_text());f=d/'waveforms.npz'
            assert sha(rp)==vc['source_sha256'] and sha(f)==vc['cache_sha256']==r['local_outputs_sha256']['waveforms.npz']
            with np.load(f) as z:e=cross(z['time'],z['out'],.6)
            e=e[e>=p['measurement_start_s']][:p['edge_count']];assert len(e)==p['edge_count'];edges.append(e)
            sources.append(dict(run=c['run'],result_sha256=sha(rp),cache_sha256=sha(f)))
        residual=edges[1]-edges[0];residual-=residual.mean();n=len(residual);freq=np.fft.rfftfreq(n,1/p['output_hz']);selected=(freq>=p['band_hz'][0])&(freq<=p['band_hz'][1]);windows=[]
        for wn,w in [('rectangular',np.ones(n)),('symmetric_hann',np.hanning(n))]:
            power=abs(np.fft.rfft(residual*w))**2/(n*np.sum(w*w));power[1:-1]*=2
            assert np.isclose(power.sum(),np.sum((residual*w)**2)/np.sum(w*w),rtol=1e-12,atol=0)
            windows.append(dict(window=wn,band_rms_fs=float(np.sqrt(power[selected].sum())*1e15),noise_energy_normalization=float(np.mean(w*w)),enbw_bins=float(n*np.sum(w*w)/np.sum(w)**2)))
        assert np.isclose(windows[0]['band_rms_fs'],v['diagnostic_band_rms_fs'],rtol=1e-12)
        rows.append(dict(method=p.get('method','traponly'),protocol_sha256=sha(pp),validation_sha256=sha(vp),sources=sources,endpoint_difference_ps=float((residual[-1]-residual[0])*1e12),windows=windows))
    comparison=[dict(window=rows[0]['windows'][i]['window'],gear_minus_trap_fs=rows[1]['windows'][i]['band_rms_fs']-rows[0]['windows'][i]['band_rms_fs'],relative_difference_percent=(rows[1]['windows'][i]['band_rms_fs']/rows[0]['windows'][i]['band_rms_fs']-1)*100) for i in (0,1)]
    out=dict(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,records=rows,comparison=comparison,samples=1024,effective_band_hz=[5285156.25,492000000.0],full_pll_acceptance=False,primary_metric_changed=False,limitations=['Window dependence mixes finite-record weighting and spectral leakage; it does not separate physical low-frequency noise, integration-method error and leakage.','The rectangular preregistered result is retained. Hann is only a sensitivity diagnostic with sum(w^2) normalization; no trend fit or spectral notches.','Changed source realization and Gear damping remain unresolved. More seeds and longer records are required; neither window gives a 10kHz full-band value.'])
    dst=H/'results/full_pll_rt4_method_window_sensitivity.json';assert not dst.exists();dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(records=[dict(method=x['method'],endpoint_difference_ps=x['endpoint_difference_ps'],windows=x['windows']) for x in rows],comparison=comparison),indent=2))


if __name__=='__main__':main()
