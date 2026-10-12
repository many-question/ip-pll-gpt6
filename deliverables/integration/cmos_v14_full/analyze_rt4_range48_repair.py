"""Analyze only the isolated 4.8fF RT4 repair protocol; no dispatch."""
import datetime, json
import numpy as np
from analyze_rt4_fast_range import H,ROOT,R,sha,analyze
P=H/'results/rt4_range48_repair_protocol.json'
OUT=ROOT/'research/rt4_range48_repair_validation_latest.json'
def main():
    p=json.loads(P.read_text());rows=[]
    for c in p['cases']:
        try:
            row=analyze(c,p)
            if row['state']=='completed':
                with np.load(R/c['run']/c['case']/'waveforms.npz') as z:
                    t=z['time'];assert np.all(np.diff(t)>0)
                    # PSF parser represents non-waveform units metadata as NaN.
                    signals=[n for n in z.files if n!='units']
                    assert all(np.all(np.isfinite(z[n])) for n in signals)
                    row['metadata_excluded_from_finiteness']=['units'] if 'units' in z.files else []
                    row['finite_waveforms']=True;row['points']=len(t)
                    if c['kind']=='capture':assert len(t)==32001 and abs(t[0])<1e-15
                    else:assert t[0]>=c['output_start_s']-1e-15
            rows.append(row)
        except Exception as e:rows.append(dict(**c,state='analysis_needs_review',reason=repr(e)))
    tunes=[c for c in rows if c['kind']=='tuning']
    gate=all(c['state']=='completed' and c['divider_ratio_ok'] for c in tunes)
    if gate:gate=tunes[0]['rf_mhz']<=2688 and tunes[1]['rf_mhz']>=3936
    s=dict(time=datetime.datetime.now().astimezone().isoformat(),protocol_sha256=sha(P),cases=rows,
        endpoint_functional_gate=gate,endpoint_gate_requires_separate_remote_terminal_audit=True,
        completed=sum(c['state']=='completed' for c in rows),expected=len(rows),candidate_adopted=False,full_pll_acceptance=False)
    OUT.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in s.items() if k!='cases'}))
if __name__=='__main__':main()
