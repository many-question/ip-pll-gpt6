"""Test a continuously running CMOS clock tree now that power is deferred.

Previous SS failures included pulse loss across the stacked NAND and following
six stages. Remove mode gating from the fast clock, retain real transistor
clock loads, and compare four balanced/skewed inverters at fixed input widths.
All divider modes remain present. No ideal internal clocks or sources.
This is a standalone candidate; reset/mode, LC loading and PVT need regression.
"""
from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
src=B/'bank_mixskew_v14.scs';base=src.read_text();cases=[]
begin=base.index('XEN0 (s1');end=base.index('XD6 (ck',begin)
for tag,sizes in [('ungatedbal',[(1,2),(3,6),(8,16),(24,48)]),
                  ('ungatedskew',[(.8,2.2),(4,5),(6,18),(32,40)])]:
    name='bank_'+tag+'_v14';lines=[];previous='q1'
    for i,(n,p) in enumerate(sizes):
        node=['ct0','ct1','cb','ck'][i]
        lines.append(f'XCT{i} ({previous} {node} vdd vss) pll_inv wn={n:g}u wp={p:g}u');previous=node
    s=(base[:begin]+'\n'.join(lines)+'\n'+base[end:]).replace('bank_mixskew_v14',name)
    (B/(name+'.scs')).write_text(s)
    for m in [6,10,14]:
        case=f'bank{tag}_m{m}_ss';cases.append(case)
        tb=(H/'tb/bankmixskew_m6_ss.scs').read_text().replace('bank_mixskew_v14',name)
        rf={6:3888,10:3120,14:3024}[m];idx={6:1,10:3,14:5}[m]
        tb=tb.replace('frequency=3888M',f'frequency={rf}M')
        for i in range(6):tb=re.sub(r'(VS'+str(i)+r' .*dc=)[^\n]+',lambda x:x[1]+('1.2' if i==idx else '0'),tb)
        tb=tb.replace(' XD.gn','').replace(' XD.ct2','')
        (H/'tb'/(case+'.scs')).write_text(tb)
(H/'results/ss_ungated_clock_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cases,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),run='bankungated01',main_dut_modified=False,condition='SS60/1.2V/10fF, actual RF receiver, measured SS tank waveform replay,200ns,last80ns,1ps/reltol1e-5',hypotheses=['Removing mode NAND reduces pulse distortion and removes a source of inactive dynamic storage.', 'Alternating P/N skew at identical stage input-width sums may restore a more useful clock window.'],not_proven=['All6modes','mode/reset transitions','LC backaction','TT/FF/temperature matrix','noise']),indent=2)+'\n')
print(' '.join(cases))
