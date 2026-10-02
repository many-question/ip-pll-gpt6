"""Finite-offset diagnostic for the exact-harmonic flicker warning.

This does not change the requested integration band or any physical device.
Results assess local peaks missed by the original logarithmic grid; it is not
a replacement full-band spectrum or an assumed low-frequency noise cutoff.
"""
from pathlib import Path
import json,datetime
H=Path(__file__).resolve().parent
f=[163990000,163999999,164000001,327990000,327999999,328000001,
   491990000,491999990,491999999]
s=(H/'tb/chain_noise_coarse_tt.scs').read_text()
assert 'start=10k stop=492M dec=10' in s
s=s.replace('start=10k stop=492M dec=10','values=['+' '.join(map(str,f))+']')
s=s.replace(' jittercal=[Jee]','')
(H/'tb/chain_alias_probe_tt.scs').write_text(s)
p=dict(created=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,
       source='chainnoise02/chain_noise_coarse_tt',offsets_hz=f,
       required_same_circuit=True,diagnostic_threshold_db=.1,
       threshold_meaning='If all finite-offset PSDs differ from interpolated coarse PSD by less than0.1dB, no material local peaking is observed down to1Hz distance. This finite set does not prove an integral through an ideal1/f singularity or full-PLL jitter.',
       sources=[dict(title='PNoise Infinite flicker noise message',url='https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/62944/pnoise-infinite-flicker-noise-message',accessed='2026-10-02',supports='Exact harmonic1/f poles can be skipped; inspect nearby frequencies. Cadence-hosted discussion, not project performance evidence.'),
                dict(title='Pnoise on signal at multiple of the fundamental',url='https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/56829/pnoise-on-signal-at-multiple-of-the-fundamental',accessed='2026-10-02',supports='Cadence staff points to Sample Ratio for clocks above PSSfund. Linked support note requires login and was not read; project RC calibration supplies numerical evidence.')])
(H/'results/chain_alias_protocol.json').write_text(json.dumps(p,indent=2)+'\n')
print('Prepared9 finite-frequency points around164/328/492MHz')
