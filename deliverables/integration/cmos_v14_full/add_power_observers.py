"""External TB-only integrated-power probes; DUT circuitry is unchanged."""
from pathlib import Path
H=Path(__file__).resolve().parent
snippet='''
// TB-only isolated1.2V/1kohm fixture validates hierarchical-current integration.
subckt instrument_check (p n)
VP (p x) vsource dc=0
R (x n) resistor r=1k
ends instrument_check
VTST (vtst 0) vsource dc=1.2
XTST (vtst 0) instrument_check
ahdl_include "tb_power_integrator.va"
BTST (power_test_w 0) bsource v=v(vtst)*i("XTST.VP:1")
BTOTAL (power_total_w 0) bsource v=-v(vdd)*i("VDD:1")
BVCO (power_vco_w 0) bsource v=-v(vdd)*i("VVCO:1")
BRX (power_rx_w 0) bsource v=-v(vdd)*i("VRX:1")
BRT (power_rt_w 0) bsource v=-v(vdd)*i("VRT:1")
XETST (power_test_w 0 energy_test_nj) tb_power_integrator
XETOTAL (power_total_w 0 energy_total_nj) tb_power_integrator
XEVCO (power_vco_w 0 energy_vco_nj) tb_power_integrator
XERX (power_rx_w 0 energy_rx_nj) tb_power_integrator
XERT (power_rt_w 0 energy_rt_nj) tb_power_integrator
save energy_test_nj energy_total_nj energy_vco_nj energy_rx_nj energy_rt_nj
'''
for p in (H/'tb').glob('range_*.scs'):
 s=p.read_text()
 if '// TB-only isolated' in s:s=s[:s.index('// TB-only isolated')]
 p.write_text(s+snippet)
print('Added passive-observation-only energy channels to future endpoint snapshots')
