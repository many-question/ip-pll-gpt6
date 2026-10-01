"""Compare nonregenerative active loads after the regenerative bracket fails."""
import json,datetime
from analyze import H
def main():
    base=(H/'tb/chain_s2_vp_tt.scs').read_text();cases=[]
    for tag,wn,wp,ib in [('a','4u','2u','20u'),('b','8u','4u','40u')]:
        name=f'mirror_{tag}_tt';p=H/'tb'/f'{name}.scs';assert not p.exists()
        s=base.replace('include "rf_clock_receiver_v8.scs"','include "rf_mirror_receiver_v8.scs"')
        s=s.replace('XRX (vp clk rx_vdd 0) tx_rf_clock_receiver_v8',f'XRX (vp vn clk rx_vdd 0) tx_rf_mirror_receiver_v8 wn={wn} wp={wp} ibias={ib}')
        s=s.replace('XRX.g0 XRX.a XRX.b','XRX.gp XRX.gn XRX.dp XRX.dn XRX.tail XRX.nb XRX.a XRX.b')
        p.write_text(s,encoding='utf-8',newline='\n');cases.append(dict(case=name,wn=wn,wp=wp,ibias=ib))
    r=dict(time=datetime.datetime.now().astimezone().isoformat(),reason='Regenerative trials show either insufficient swing or latched states. Test a continuous differential current-steering amplifier with active mirror load.',
        change='Differential NMOS pair,PMOS mirror load,1:5 tail mirror,0.9V resistor-derived input bias,then0.5u/2u/8u NMOS inverter chain. Retimer scale2/output scale4.',
        cases=cases,criteria='Original output_v8 functional criteria. IREF and ideal R/C explicitly retained; no fullPLL power/noise or PVT claim.')
    (H/'results/mirror_protocol.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
