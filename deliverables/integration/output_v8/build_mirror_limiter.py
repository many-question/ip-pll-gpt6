"""Recover common mode between RF gain stages instead of cascading DC offsets."""
import datetime,json
from analyze import H
def main():
    b=H.parents[1]/'blocks/output_v8';src=(b/'rf_mirror_receiver_v8.scs').read_text()
    start=src.index('X0 (dn a');end=src.index('ends tx_rf_mirror_receiver_v8')
    for n in [2,3]:
        name=f'tx_rf_mirror_gain{n}_v8';p=b/f'rf_mirror_gain{n}_v8.scs';assert not p.exists()
        s=(src[:start]+f'XGAIN (dn clk vdd vss) tx_limiter{n} wn=4u wp=10u\n'+src[end:]).replace('tx_rf_mirror_receiver_v8',name)
        p.write_text(s,encoding='utf-8',newline='\n')
        tb=H/'tb'/f'mirror_gain{n}_tt.scs';assert not tb.exists()
        s=(H/'tb/mirror_b_tt.scs').read_text().replace('rf_mirror_receiver_v8.scs',p.name).replace('tx_rf_mirror_receiver_v8',name)
        s=s.replace('XRX.a XRX.b','XRX.XGAIN.g0 XRX.XGAIN.o0 XRX.XGAIN.g1 XRX.XGAIN.o1')
        tb.write_text(s,encoding='utf-8',newline='\n')
    r=dict(time=datetime.datetime.now().astimezone().isoformat(),source='mirror_b_tt differential amplifier dn spans0.235..1.006V, but downstream DC-coupled first output averages0.479V and next inverter sticks high; mirror_a has the opposite DC offset.',
        change='Preserve the faster8u/4u/40uA mirror front. Use existing equal-width AC-coupled self-biased tx_limiter2/3,then its8u output driver. This reduces gain-stage fanout and restores each stage common mode.',
        criteria='Keep output_v8 functional criteria and preserve all failed variants. Ideal current-reference/passive assumptions remain.')
    (H/'results/mirror_gain_protocol.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
