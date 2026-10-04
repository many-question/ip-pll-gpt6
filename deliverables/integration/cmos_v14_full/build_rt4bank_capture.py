"""Integrate the verified new divider and RT4 in a separate complete-PLL candidate."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
warm=H/'results/rt4_release_extension_validation.json';w=json.loads(warm.read_text())
audit=H/'results/rt4_pulsetrip_audit_validation.json';a=json.loads(audit.read_text())
assert w['functional_warm_capture_passed'] and all(w['checks'].values())
assert a['complete'] and a['passed']
source=B/'pll_capture_v14.scs';s=source.read_text();name='pll_capture_rt4bank_v14'
top=B/(name+'.scs');assert not top.exists()
s=s.replace('pll_capture_v14',name).replace('cmos_even_bank_acq_v14','bank_pulsetrip_v14').replace('rt_light24s12_out083_v14','rt_noise_scale4_v14')
top.write_text(s)
# Assert that the entire complete-PLL change is exactly the two reviewed
# module replacements; no slow controls or bias sources are idealized.
restored=s.replace(name,'pll_capture_v14').replace('bank_pulsetrip_v14','cmos_even_bank_acq_v14').replace('rt_noise_scale4_v14','rt_light24s12_out083_v14')
assert restored==source.read_text()
src=H/'tb/repair_capture_tt.scs';body=src.read_text().replace('pll_capture_v14',name)
assert 'maxstep=4p' in body and 'reltol=1e-4' in body and 'stop=64u' in body and 'readic=' not in body and 'recover=' not in body
case='rt4bank_capture_tt';run='rt4bankcold01';save='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/'+run+'_'+case+'.srf'
body=re.sub(r'^(tran tran .*)$',lambda m:m[0]+f' savetime=[8u 16u 32u 48u 64u] savefile="{save}"',body,flags=re.M)
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
p=dict(scope=__doc__,run=run,case=case,time=datetime.datetime.now().astimezone().isoformat(),
    source_top_sha256=sha(source),candidate_top_sha256=sha(top),source_tb_sha256=sha(src),candidate_tb_sha256=sha(tb),
    warm_capture_validation_sha256=sha(warm),noise_gate_validation_sha256=sha(audit),
    changed_modules=['cmos_even_bank_acq_v14 -> bank_pulsetrip_v14','rt_light24s12_out083_v14 -> rt_noise_scale4_v14'],
    retained='All actual control/FLL/watchdog/reference/sampler/CP/loopfilter/VCO/bias circuits and all external reset/apply/K41 stimuli from original full PLL.',
    condition='Complete transistor PLL candidate,TT27/1.2V/24MHz/K41/M4/10fF/Q5RLC/CF10,64us independent reset,4ps/1e-4/trap. DCsupply established and10uV differential oscillator seed as before.',
    native_checkpoints_s=[8e-6,16e-6,32e-6,48e-6,64e-6],native_savefile=save,
    expected_cost='Same original4ps64us fullPLL with8threads took8h11m; runtime is not guaranteed. Use released fourthlongslot,8threads,total<=18/fourlong+oneshort.',
    analysis_command='analyze_capture.py rt4bankcold01 --case rt4bank_capture_tt --fine-window 128 --precision functional',
    limitations=['Functional4psscreen only; not numerical convergence or randomjitter.','WarmRT4capture doesnotprove independentreset/FLLhandoff.','Reference24MHz/oneTTfrequency only; other33points/PVT/recovery unverified.','No CF40/biasR2000/4.8fF/dummy adoption.','The original mainDUT remains unchanged; this separate candidate must pass integration before adoption.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4bank_capture_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case)
