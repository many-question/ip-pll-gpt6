"""Exercise the repaired MOS bank with actual RF receiver and counter loading.

The external source replays a TT VCO waveform at each target frequency. This
is an interface regression, not a loaded SS oscillator or full PLL result.
"""
from pathlib import Path
import json,re
H=Path(__file__).resolve().parent
freq={4:3936,6:3888,8:3456,10:3120,12:3168,14:3024}
cases=[]
loads=(H/'tb/chain_noise_fine_tt.scs').read_text().split('// Same clock mux')[1].split('// Full divider-tree')[0]
loads=loads.replace('(out clock_mux','(data clock_mux')
for m,f in freq.items():
 case=f'bankboostrf_m{m}_ss';cases.append(case)
 s=(H/'tb'/f'bankboostreg_m{m}_ss.scs').read_text()
 s=s.replace('include "digital_cells_v2.scs"','include "digital_cells_v2.scs"\ninclude "fll_circuit.scs"\ninclude "rf_light24s12_v14.scs"')
 s=re.sub(r'^VCLK .*$',f'ahdl_include "tank_replay_full_v14.va"\nXRF (vp vn 0) tank_replay_full_v14 frequency={f}M\nXRX (vp clk vdd 0) rf_light24s12_v14',s,flags=re.M)
 s=s.replace('tran tran','// Same clock mux'+loads+'\ntran tran')
 s+='save vp vn clock_mux count_clock\n'
 (H/'tb'/(case+'.scs')).write_text(s)
 scope='SS60/1.2V/10fF/100ns,last40ns; same repaired MOS bank, actual MOS RF receiver, retimer/output and quiet physical counter/mux load. External TT VCO waveform frequency-scaled, not SS VCO amplitude/noise/back-action, not complete PLL.1ps/reltol1e-5.'
(H/'results/ss_rf_protocol.json').write_text(json.dumps(dict(cases=cases,scope=scope,candidate='bank_preboost50_v14',adopted_in_pll=False),indent=2)+'\n')
print(' '.join(cases))
