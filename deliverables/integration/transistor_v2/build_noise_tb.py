from pathlib import Path
from build_receiver import head,MODEL
H=Path(__file__).resolve().parent
def main():
    for code,fund in [(0,4e9),(127,3.1e9),(255,2.62e9)]:
        lines=[head(),f'include "{MODEL}" section=tt_bbmvar','simulator lang=spectre insensitive=no',
        'include "lc_vco_candidate.scs"','VDD (vdd 0) vsource dc=1.2','VC (ctrl 0) vsource dc=.6']
        lines +=[f'VB{i} (b{i} 0) vsource dc={1.2 if code&(1<<i) else 0}' for i in range(8)]
        lines+=['XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vdd 0) tx_lc_vco_candidate',
        'ic vp=1.20001 vn=1.2',f'pss (vp vn) pss fund={fund} harms=15 tstab=200n maxstep=5p errpreset=conservative saveinit=yes',
        'pn (vp vn) pnoise start=10k stop=500M dec=20 maxsideband=15 noiseout=[usb am pm] sweeptype=relative relharmnum=1',
        'save vp vn XV.XL.tail VDD:p','saveOptions options save=selected']
        (H/'tb'/f'tb_vco_noise_c{code}.scs').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
