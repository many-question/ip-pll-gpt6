"""Compare adjacent externally fixed codes with identical callback geometry and stimuli."""
from pathlib import Path
import datetime, json
import numpy as np
from review_pdk_callback110 import ROOT, H, sha, stats


def main():
    out = H/'results/rt4_callback_k41_comparison114.json'
    assert not out.exists()
    paths = [H/'results'/('rt4_callback_'+s+'_114_review.json') for s in ('k41','k41b')]
    reviews = [json.loads(p.read_text()) for p in paths]
    protocols = [json.loads((H/'results'/('rt4_callback_'+s+'_114_protocol.json')).read_text()) for s in ('k41','k41b')]
    assert all(p['physical_inputs_sha256']['share/deliverables/blocks/cmos_v14_full/rt4_callback110_after.scs']=='260a50e7e62d0d25cfdfb21d6004a22f31ca38544632329448bea811dcd38f62' for p in protocols)
    bias = []
    for p, r in zip(protocols, reviews):
        c=p['cases'][0]
        npz=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']/'waveforms.npz'
        assert sha(npz)==r['waveforms_sha256']
        with np.load(npz) as z:
            t=z['time']
            bias.append([stats(t,z['XV.XL.nb'],*s['window_s']) for s in r['segments']])
    rows=[]
    for i,(a,b) in enumerate(zip(reviews[0]['segments'],reviews[1]['segments'])):
        assert a['coarse']==9 and b['coarse']==8 and a['control_V']==b['control_V'] and a['window_s']==b['window_s']
        rows.append(dict(control_V=a['control_V'],window_s=a['window_s'],
            code9_RF_MHz=a['rf']['frequency_Hz']/1e6,code8_RF_MHz=b['rf']['frequency_Hz']/1e6,
            code8_minus_code9_RF_MHz=(b['rf']['frequency_Hz']-a['rf']['frequency_Hz'])/1e6,
            code8_minus_code9_nfilt_mean_mV=1000*(b['nfilt']['mean']-a['nfilt']['mean']),
            code9_nb=bias[0][i],code8_nb=bias[1][i],
            nfilt_drift_V_per_us=dict(code9=a['nfilt_linear_drift_V_per_us'],code8=b['nfilt_linear_drift_V_per_us']),
            approximate_resistor_only_drift_V_per_us=dict(code9=(bias[0][i]['mean']-a['nfilt']['mean'])/10,code8=(bias[1][i]['mean']-b['nfilt']['mean'])/10)))
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),
        evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in paths],
        rows=rows,code8_conditional_bracketed=reviews[1]['conditional_k41_bracketed'],
        code8_worst_margin_MHz=dict(below_target=3936-reviews[1]['worst_100ns_window_endpoint_MHz']['low_max'],above_target=reviews[1]['worst_100ns_window_endpoint_MHz']['high_min']-3936),
        nominal_bias_RC_us=10,
        boundary='Matched independent warm-bias local records; b3..b7 tail enables unchanged, b0 alone differs. The resistor-only slope estimate omits RF capacitive coupling and is not a prediction of asymptotic bias or frequency. No full-PLL selection, lock, or noise evidence.')
    out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,indent=2))


if __name__ == '__main__':
    main()
