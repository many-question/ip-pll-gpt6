from build import *

# Keep the previous source variants immutable in their input snapshots.
# A weak pull-up defines OFF bottom-plate DC and avoids forward body-diode
# clamping of otherwise floating OFF capacitors. ON loading is measured.
s=(B.parent/'transistor_v1/cap_bank_experiment.scs').read_text()
s=s.replace('tx_cap_bank_experiment','tx_cap_bank_v4').replace(' b7 vss)',' b7 vdd vss)')
s=s.replace('unit_w=2.4u','unit_w=2.4u off_r=1Meg')
s=s.replace('ends tx_cap_bank_v4',''.join(f'RB{i} (x{i} vdd) resistor r=off_r\n' for i in range(8))+'ends tx_cap_bank_v4')
(B/'cap_bank_v4.scs').write_text(s)
s=(B/'lc_vco_v4n.scs').read_text().replace('tx_lc_vco_v4n','tx_lc_vco_v4b').replace('cap_bank_experiment','cap_bank_v4')
s=s.replace('XBP (vp b0 b1 b2 b3 b4 b5 b6 b7 vss)','XBP (vp b0 b1 b2 b3 b4 b5 b6 b7 vdd vss)')
s=s.replace('XBN (vn b0 b1 b2 b3 b4 b5 b6 b7 vss)','XBN (vn b0 b1 b2 b3 b4 b5 b6 b7 vdd vss)')
(B/'lc_vco_v4b.scs').write_text(s)
plans=[('wide_small_sw',dict(core=120e-6,switch=1.2e-6,l=1.6e-9)),
       ('wide_bias',dict(kind='b',core=120e-6,l=1.6e-9)),
       ('wide_bias_l18',dict(kind='b',core=120e-6,l=1.8e-9,unit=5.7e-15)),
       ('wide_bias_i95',dict(kind='b',core=100e-6,l=1.8e-9,ibias=95e-6,unit=5.7e-15)),
       ('wide_bias_sw',dict(kind='b',core=120e-6,l=1.8e-9,unit=5.7e-15,switch=1.2e-6)),
       ('wide_bias_l20',dict(kind='b',core=120e-6,l=2e-9,unit=5e-15,switch=1.2e-6))]
for tag,p in plans:
    for code in [0,255]:bench(f'r2_{tag}_c{code}',code=code,proxy=140e-15,stop=160e-9,**p)
