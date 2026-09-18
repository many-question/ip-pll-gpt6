from build import *
s='''simulator lang=spectre
// Differential capacitors share one NMOS bridge. The weak DC paths set
// bottom plates high when OFF and near ground when ON; all devices are PDK MOS.
subckt tx_cap_bank_diff_v4 (vp vn b0 b1 b2 b3 b4 b5 b6 b7 vdd vss)
parameters unit_c=6f unit_w=1.2u off_r=1Meg
'''
for i in range(8):
    k=2**i
    s+=f'''CP{i} (vp xp{i}) capacitor c=unit_c*{k}
CN{i} (vn xn{i}) capacitor c=unit_c*{k}
M{i} (xp{i} b{i} xn{i} vss) nch w=unit_w*{k} l=180n ad=unit_w*{k}*240n as=unit_w*{k}*240n pd=2*(unit_w*{k}+240n) ps=2*(unit_w*{k}+240n)
XI{i} (b{i} bb{i} vdd vss) pll_inv wn=300n wp=750n
RP{i} (xp{i} bb{i}) resistor r=off_r
RN{i} (xn{i} bb{i}) resistor r=off_r
'''
s+='ends tx_cap_bank_diff_v4\n'
(B/'cap_bank_diff_v4.scs').write_text(s)
s=(B/'lc_vco_v4n.scs').read_text().replace('tx_lc_vco_v4n','tx_lc_vco_v4d').replace('cap_bank_experiment.scs','cap_bank_diff_v4.scs')
i=s.index('XBP (');j=s.index('CVP (')
s=s[:i]+'XB (vp vn b0 b1 b2 b3 b4 b5 b6 b7 vdd vss) tx_cap_bank_diff_v4 unit_c=unit_c unit_w=unit_w\n'+s[j:]
(B/'lc_vco_v4d.scs').write_text(s)
for tag,p in [('n80w12',dict(core=80e-6,switch=1.2e-6)),('n80w18',dict(core=80e-6,switch=1.8e-6)),('n120w12',dict(core=120e-6,switch=1.2e-6))]:
    for code in [0,255]:bench(f'diff_{tag}_c{code}',kind='d',code=code,l=1.8e-9,unit=6e-15,proxy=140e-15,stop=160e-9,**p)
