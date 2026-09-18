from build import *

# Replace the exploratory weak resistive pulls with OFF-only PDK PMOS clamps.
# This removes ON-state pull-up current and settles the largest bottom plate
# much faster after a coarse-code update. Small clamps limit OFF RF loading.
s=(B.parent/'transistor_v1/cap_bank_experiment.scs').read_text()
s=s.replace('tx_cap_bank_experiment','tx_cap_bank_switched_v4').replace(' b7 vss)',' b7 vdd vss)')
s=s.replace('unit_w=2.4u','unit_w=1.2u clamp_w=300n')
s=s.replace('ends tx_cap_bank_switched_v4',''.join(
    f'MP{i} (x{i} b{i} vdd vdd) pch w=clamp_w l=180n ad=clamp_w*240n as=clamp_w*240n pd=2*(clamp_w+240n) ps=2*(clamp_w+240n)\n' for i in range(8))+'ends tx_cap_bank_switched_v4')
(B/'cap_bank_switched_v4.scs').write_text(s)
s=(B/'lc_vco_v4b.scs').read_text().replace('tx_lc_vco_v4b','tx_lc_vco_v4s').replace('cap_bank_v4','cap_bank_switched_v4')
(B/'lc_vco_v4s.scs').write_text(s)
P=dict(kind='s',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
for c in ['tt','ss','ff']:
    for code,m in [(0,4),(255,14)]:
        bench(f'switched_{c}_c{code}_m{m}',code=code,m=m,corner=c,loaded=True,stop=200e-9,**P)
        bench(f'switched_proxy_{c}_c{code}',code=code,corner=c,proxy=140e-15,stop=160e-9,**P)
