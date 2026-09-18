"""Public VCO entry with defaults equal to the explicit, tested repair values."""
from build import B,H
import re
s=(B/'lc_vco_v4r.scs').read_text().replace('tx_lc_vco_v4r','tx_lc_vco_repaired')
s=re.sub(r'parameters .*\n',
         'parameters fixed_c=10f tank_l=2n series_r=6.8224303440060226 cscale=1 core_w=120u ibias=80u unit_c=4.4f unit_w=1.2u fine_w=4.5u boost_unit=500n\n',s)
(B/'lc_vco_repaired.scs').write_text(s)
# An actual default-parameter smoke test, rather than just checking text equality.
s=(H/'tb/r2_explicit_defaults.scs').read_text().replace('lc_vco_v4r.scs','lc_vco_repaired.scs')
s=re.sub(r'XV (.*) tx_lc_vco_v4r .*\n',r'XV \1 tx_lc_vco_repaired\n',s)
(H/'tb/r2_public_defaults.scs').write_text(s)
