"""Observe the unchanged failing SS divider before making a circuit repair."""
from pathlib import Path
H=Path(__file__).resolve().parent
for m in [6,10,14]:
    s=(H/'tb'/f'bankrt_m{m}_ss.scs').read_text()
    s=s.replace('stop=100n outputstart=60n','stop=30n')
    s=s.replace('saveOptions options',
        'save XD.q0 XD.qb0 XD.ci XD.gn XD.cb XD.run XD.loadb XD.XRL.a XD.XRL.b '+
        'XD.XF0.din XD.XF0.qm XD.XF0.XM.x XD.XF0.XS.x '+
        'XD.XD6.clkb XD.XD6.X0.qm XD.XD6.X0.XM.x XD.XD6.X0.XS.x\n'+
        'saveOptions options')
    (H/'tb'/f'bankdiag_m{m}_ss.scs').write_text(s)
