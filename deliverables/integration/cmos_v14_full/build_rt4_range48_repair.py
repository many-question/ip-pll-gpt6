"""Isolated RT4 4.8fF candidate; two endpoint gates before four affected captures."""
from pathlib import Path
import datetime, hashlib, json
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    pth=H/'results/rt4_range48_repair_protocol.json'
    assert not pth.exists(), 'Issued protocol must not be replaced'
    baseline=H/'results/rt4_adopted_baseline.json'
    b=json.loads(baseline.read_text())
    for d in b['dependencies']:assert sha(ROOT/d['path'])==d['sha256']
    source=ROOT/'share/deliverables/blocks/cmos_v14_full/pll_capture_rt4bank_v14.scs'
    target=source.with_name('pll_capture_rt4bank_range48_v14.scs')
    assert not target.exists()
    s=source.read_text().replace('pll_capture_rt4bank_v14','pll_capture_rt4bank_range48_v14')
    old=') lc_vco_physical_v14 bias_r=bias_r'
    assert s.count(old)==1
    s=s.replace(old,old+' unit_c=4.8f')
    target.write_text('// Independent range-repair candidate; adopted RT4 baseline remains unchanged.\n'+s,encoding='utf8')
    prior=json.loads((H/'results/rt4_fast_range_protocol.json').read_text())
    rows=[]
    for oldcase,case,run in [('rt4_fast_range_c255_v02','rt4r48_range_c255_v02','rt4r48lowssd01'),('rt4_fast_range_c0_v10','rt4r48_range_c0_v10','rt4r48highssd01')]+[(f'rt4_fast_k{k}_tt',f'rt4r48_k{k}_tt',f'rt4r48k{k}ssd01') for k in [14,19,28,41]]:
        row=next(c.copy() for c in prior['cases'] if c['case']==oldcase)
        src=H/'tb'/(oldcase+'.scs'); assert sha(src)==row['tb_sha256']
        s=src.read_text()
        if row['kind']=='tuning':
            old=') lc_vco_physical_v14 bias_r=2500';assert s.count(old)==1
            s=s.replace(old,old+' unit_c=4.8f')
        else:s=s.replace('pll_capture_rt4bank_v14','pll_capture_rt4bank_range48_v14')
        assert '/home/jielu' not in s and 'readic=' not in s and 'recover=' not in s
        tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(s,encoding='utf8')
        row.update(case=case,run=run,tb_sha256=sha(tb),source_case=oldcase,source_tb_sha256=sha(src))
        rows.append(row)
    p=dict(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,candidate_top=target.relative_to(ROOT).as_posix(),candidate_sha256=sha(target),
        adopted_baseline=dict(path=baseline.relative_to(ROOT).as_posix(),sha256=sha(baseline)),baseline_top_sha256=sha(source),
        change='Only XV unit_c override4.4fF->4.8fF; no controller, divider, RT4, sampler, Q5, CF10, or bias changes. Candidate not adopted.',
        cases=rows,mode='ax',preset_override='all',maxstep_s=8e-12,reltol=1e-3,vabstol=1e-6,iabstol=1e-12,method='traponly',noise=False,
        condition=prior['condition'].replace('4.4fF','candidate4.8fF'),capture_screen=prior['capture_screen'],capture_initialization=prior['capture_initialization'],
        dispatch_gate='Only after both400ns endpoints exit0, raw END, complete finite waveforms, local/remote hashes, divider ratio and RF<=2688MHz / >=3936MHz; then four affected64us TT captures. Failure halts queue; never replay.',
        target_rf_range_mhz=[2688,3936],resource_cap=dict(threads=18,long_jobs=4,short_jobs=1),
        capture_purposes={'14':'336MHz lowRF/M8 failure repair','19':'456MHz lowRF/M6 failure repair','28':'672MHz lowRF/M4 failure repair','41':'984MHz same candidate capture/coarse-selection check'},
        evidence_boundary='Endpoint fixture is externally clamped, not closed-loop. Old4.8fF fixture uses different divider/retimer. No noise or whole-band acceptance transfer; no33-point/PVT/method/seed matrix.',
        source_protocol_sha256=sha(H/'results/rt4_fast_range_protocol.json'),full_pll_jitter_acceptance=False)
    pth.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(protocol=str(pth),shorts=2,conditional_captures=4)))
if __name__=='__main__':main()
