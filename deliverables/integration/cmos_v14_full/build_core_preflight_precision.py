"""Separate boundary/initial-state effects from solver tolerance effects."""
from pathlib import Path
H=Path(__file__).resolve().parent
s=(H/'tb/core_preflight_tt.scs').read_text()
s=s.replace('reltol=1e-5','reltol=1e-4').replace('maxstep=1p','maxstep=4p')
(H/'tb/core_preflight_4ps_tt.scs').write_text(s)
print('Prepared 1us same-core/same-IC transient:4ps/reltol1e-4,absolute tolerances remain strict; not noise.')
