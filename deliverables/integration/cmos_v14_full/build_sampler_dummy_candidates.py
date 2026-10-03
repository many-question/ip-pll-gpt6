"""Prepare MOS dummy-sampler candidates; no launch or adoption is implied.

Direct periodic loading is supported by the saved trajectory but still awaits
the externalVCTRL clamp control. This prepares a bounded40/80/120f sweep for
the released short slot only after those controls have been reviewed.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
source=B/'pll_noise_pulsetrip_core_v14.scs';original=source.read_text()
body=original.replace('pll_noise_pulsetrip_core_v14','pll_noise_dummy_core_v14')
body=body.replace('ref_load=0','ref_load=0 cdummy=80f')
body=body.replace('include "sampler_bias_v5.scs"','include "sampler_bias_v5.scs"\ninclude "sampler_dummy_v14.scs"')
body=body.replace('XS (refb sp sn hp hn vdd vss) tx_sampler','XS (refb sp sn hp hn vdd vss) sampler_dummy_v14 cdummy=cdummy')
assert body!=original and body.count('sampler_dummy_v14 cdummy=cdummy')==1
reversed_body=body.replace('pll_noise_dummy_core_v14','pll_noise_pulsetrip_core_v14').replace('ref_load=0 cdummy=80f','ref_load=0').replace('\ninclude "sampler_dummy_v14.scs"','').replace('sampler_dummy_v14 cdummy=cdummy','tx_sampler')
assert reversed_body==original
target=B/'pll_noise_dummy_core_v14.scs';assert not target.exists();target.write_text(body)
base=(H/'tb/samplerload_clocked_tt.scs').read_text();rows=[]
for cf in [40,80,120]:
    case=f'samplerdummy_c{cf}_tt'
    tb=base.replace('pll_noise_pulsetrip_core_v14','pll_noise_dummy_core_v14').replace('ref_load=1.9p','ref_load=1.9p cdummy='+str(cf)+'f')
    tb+='\nsave XP.XS.hpd XP.XS.hnd XP.XS.refb\n'
    p=H/'tb'/(case+'.scs');assert not p.exists();p.write_text(tb)
    rows.append(dict(case=case,cdummy_f=cf*1e-15,tb_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
out=dict(scope=__doc__,status='prepared_not_run',run='samplerdummy01',cases=rows,
    original_core_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_core_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    sampler_sha256=hashlib.sha256((B/'sampler_dummy_v14.scs').read_bytes()).hexdigest(),
    exact_core_reversal_verified=True,
    physical_change='Two additional complementary-clocked MOS transmission gates and dummy capacitors. Main holdcapacitors/switches/inverter unchanged; inverter/refclock loading increases physically.',
    acceptance_boundary='Same clamped-control750ns diagnostic as samplerload_clocked_tt, not closed-loopPLL/noise acceptance.',
    launch_gate='Review samplerload01 fixedcontrol evidence first; no automatic dispatch. Reuse its1threadshortslot only once released.',
    limitations=['Dummy values are explicit trial parameters, not extracted replicas of CP/detector input capacitance.',
        'Mismatch, extra device noise, charge injection, changed reference slew, VCO load/range, and closed-loop capture remain to be verified.',
        'No CML buffer or new main architecture has been adopted.'],
    source='Gao etal.,JSSC2010,DOI10.1109/JSSC.2010.2053094,SectionIII.A: complementary dummy sampling can compensate switched capacitive loading; applicabilityhereisahypothesis.',
    source_url='https://ris.utwente.nl/ws/files/6782511/Gao_IEEE_JSSC_sept_2010.pdf',
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/sampler_dummy_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print('Prepared only:',','.join(x['case'] for x in rows))
