from build import *

s=(B/'lc_core_v4n.scs').read_text().replace('tx_lc_core_v4n','tx_lc_core_v4r')
s=s.replace('(vp vn vdd vss)','(vp vn b3 b4 b5 b6 b7 vdd vss)')
s=s.replace('cscale=1','cscale=1 boost_unit=500n')
extra='// Upper five coarse bits add a gradual tail-current slope.\n// Source gating leaves every mirror gate on the quiet, continuously filtered bias.\n'
for i in range(3,8):
    k=2**(i-3)
    extra+=f'''MA{i} (tail nfilt s{i} vss) nch w=boost_unit*{k} l=1u ad=boost_unit*{k}*240n as=boost_unit*{k}*240n pd=2*(boost_unit*{k}+240n) ps=2*(boost_unit*{k}+240n)
ME{i} (s{i} b{i} vss vss) nch w=boost_unit*4*{k} l=180n ad=boost_unit*4*{k}*240n as=boost_unit*4*{k}*240n pd=2*(boost_unit*4*{k}+240n) ps=2*(boost_unit*4*{k}+240n)
'''
s=s.replace('ends tx_lc_core_v4r',extra+'ends tx_lc_core_v4r')
(B/'lc_core_v4r.scs').write_text(s)
s=(B/'lc_vco_v4s.scs').read_text().replace('tx_lc_vco_v4s','tx_lc_vco_v4r').replace('lc_core_v4n','lc_core_v4r')
s=s.replace('fine_w=3u','fine_w=3u boost_unit=500n')
s=s.replace('XL (vp vn vdd vss)','XL (vp vn b3 b4 b5 b6 b7 vdd vss)').replace('ibias=ibias cscale=cscale','ibias=ibias cscale=cscale boost_unit=boost_unit')
(B/'lc_vco_v4r.scs').write_text(s)
P=dict(kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
for c in ['tt','ss','ff']:
    for code,m in [(0,4),(255,14)]:
        bench(f'seg_{c}_c{code}_m{m}',code=code,m=m,corner=c,loaded=True,stop=200e-9,**P)
        bench(f'seg_proxy_{c}_c{code}',code=code,corner=c,proxy=140e-15,stop=160e-9,**P)
