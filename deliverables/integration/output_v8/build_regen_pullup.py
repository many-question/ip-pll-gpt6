"""Increase regeneration pull-up after internal-waveform diagnosis."""
import json,datetime
from analyze import H
def main():
    cases=[]
    for tag,wn,wp,ib in [('d','8u','2.4u','10u'),('e','16u','4.8u','20u')]:
        for phase in ['p','n']:
            name=f'regen_{tag}_{phase}_tt';dest=H/'tb'/f'{name}.scs';assert not dest.exists()
            s=(H/'tb'/f'regen_a_{phase}_tt.scs').read_text().replace('wn=8u wp=600n ibias=10u',f'wn={wn} wp={wp} ibias={ib}')
            dest.write_text(s,encoding='utf-8',newline='\n');cases.append(dict(case=name,wn=wn,wp=wp,ibias=ib))
    record=dict(time=datetime.datetime.now().astimezone().isoformat(),source='regen_a_p_tt measured internal qp/qn range0.009..0.373V; following MOS inverter never switches.',
        hypothesis='Weak regenerative PMOS cannot recharge internal capacitance within127ps half-cycle. Increase PMOS/NMOS strength ratio and evaluate both output polarities.',
        cases=cases,criteria='Unchanged output_v8 functional criteria; circuit investigation, not selected or noise-qualified.')
    (H/'results/pullup_protocol.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
