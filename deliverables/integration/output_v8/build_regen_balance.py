"""Bracket regenerative pull-up/input strength using preserved internal waveforms."""
import json,datetime
from analyze import H
def main():
    cases=[]
    for tag,wn,wp,ib in [('f','8u','1.2u','10u'),('g','8u','1.5u','20u'),('h','16u','2.4u','20u')]:
        name=f'regen_{tag}_p_tt';dest=H/'tb'/f'{name}.scs';assert not dest.exists()
        s=(H/'tb/regen_a_p_tt.scs').read_text().replace('wn=8u wp=600n ibias=10u',f'wn={wn} wp={wp} ibias={ib}')
        dest.write_text(s,encoding='utf-8',newline='\n');cases.append(dict(case=name,wn=wn,wp=wp,ibias=ib))
    r=dict(time=datetime.datetime.now().astimezone().isoformat(),reason='Weak0.6u PMOS leaves both internal outputs below inverter threshold;2.4u PMOS with8u input instead latches one side high and cannot be overturned. Test intermediate pull-up and input bias.',
        cases=cases,criteria='Keep original functional criteria. This is a bracketed feasibility exploration; no PVT/robustness/noise claim.')
    (H/'results/balance_protocol.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
