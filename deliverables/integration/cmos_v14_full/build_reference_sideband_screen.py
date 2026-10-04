"""Test whether fewer PNoise sidebands preserve the actual refined spectrum.

Fresh PSS is retained. The measured 2047-sideband baseline is immutable in
this protocol; its parent precision summary may later gain candidate results.
Do not apply a lower count anywhere else until this comparison has passed.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dest=H/'results/reference_sideband_screen_protocol.json';assert not dest.exists()
    proof=H/'results/reference_buffer_precision_validation.json';v=json.loads(proof.read_text());b=v['cases'][0]
    assert b['variant']=='baseline' and b['noise_valid'] and b['precision']['passed']
    rp=ROOT/b['source_result'];assert sha(rp)==b['source_sha256']
    pp=H/'results/reference_buffer_precision_protocol.json';p=json.loads(pp.read_text())
    assert v['protocol_sha256']==sha(pp)
    src=H/'tb'/(b['case']+'.scs');assert sha(src)==p['cases'][0]['tb_sha256']
    rows=[]
    for sb in [31,127]:
        body=src.read_text();assert body.count('maxsideband=2047')==1
        body=body.replace('maxsideband=2047',f'maxsideband={sb}')
        case=f'reference_sideband{sb}_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
        tb.write_text(body,encoding='utf-8',newline='\n')
        rows.append(dict(case=case,run='refsidebandscreen01',maxsideband=sb,tb_sha256=sha(tb)))
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
        baseline_case=b,baseline_case_snapshot_sha256=hashlib.sha256(json.dumps(b,sort_keys=True).encode()).hexdigest(),
        source_precision_protocol_sha256=sha(pp),source_precision_summary_sha256_at_build=sha(proof),
        source_case_tb_sha256=sha(src),dependencies_sha256=p['cases'][0]['dependencies_sha256'],condition=p['condition'],
        numerical_settings_except_sidebands=p['numerical_settings'],integration_band_hz=p['integration_band_hz'],
        precision_limits=p['precision_limits'],fresh_pss=True,main_dut_modified=False,full_pll_acceptance=False,
        rationale='Existing fresh-PSS 2047-sideband run supplies a measured comparison. If a smaller count agrees over the full grid, later similar standalone sweeps can be made cheaper without changing their accuracy gate.',
        launch_scope='Two serial one-thread cases, 900s per-case guard; only when actual resource capacity is available. Not yet launched.',
        limitations=['A pass applies to this reference-buffer baseline only, not automatically to the resized buffer, nonlinear frontend, VCO or full PLL.',
            'No PSS state reuse. No relaxation of the 0.1dB full-grid / 1% integrated-RMS comparison.',
            'The parent precision summary is cumulative; the exact baseline case and raw-file hashes are frozen here.'])
    dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(cases=rows,launched=False),indent=2))

if __name__=='__main__':main()
