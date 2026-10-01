"""Try existing differential regeneration after the linear inverter chain fails."""
import json,datetime
from analyze import H
def main():
    base=(H/'tb/chain_s2_vp_tt.scs').read_text()
    cases=[]
    for tag,wn,wp,ib in [('a','8u','600n','10u'),('b','16u','1.2u','10u'),('c','16u','1.2u','20u')]:
        for phase in ['p','n']:
            name=f'regen_{tag}_{phase}_tt';p=H/'tb'/f'{name}.scs';assert not p.exists()
            s=base.replace('include "rf_clock_receiver_v8.scs"','include "receiver.scs"')
            s=s.replace('XRX (vp clk rx_vdd 0) tx_rf_clock_receiver_v8',
                f'XRX (vp vn rcp rcn rx_vdd 0) tx_regen_receiver wn={wn} wp={wp} ibias={ib} cc=240f\nXRB (rc{phase} clk rx_vdd 0) pll_inv wn=8u wp=20u')
            s=s.replace('XRX.g0 XRX.a XRX.b','XRX.gp XRX.gn XRX.qp XRX.qn rcp rcn')
            p.write_text(s,encoding='utf-8',newline='\n');cases.append(dict(case=name,wn=wn,wp=wp,ibias=ib,polarity=phase))
    record=dict(time=datetime.datetime.now().astimezone().isoformat(),reason='The new3-inverter linear clock receiver attenuates the3.936GHz input and cannot provide valid clock rails with retimer load; initial scale2/4 cases fail functionality.',
        change='Use existing physical differential regenerative receiver,cc240f,plus8u/20u MOS output inverter. Retimer scale2/output scale4. Three input/regeneration/bias choices and two output polarities.',
        criteria='Keep original protocol functional/swing criteria. IREF is an explicit ideal current-reference assumption; supplies and both receiver output chains are counted.',cases=cases,
        scope='RF driven output-chain fixture; no real VCO/mainloop/FLL or noise conclusion.')
    (H/'results/regen_protocol.json').write_text(json.dumps(record,indent=2)+'\n')
    print(' '.join(x['case'] for x in cases))
if __name__=='__main__':main()
