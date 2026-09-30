"""Fixed coarse-code LC loop; not FLL acquisition or complete output-chain validation."""
from pathlib import Path
import argparse,re
H=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--preset',type=float,required=True);ap.add_argument('--name',default='loop_both');ap.add_argument('--r',default='100k');ap.add_argument('--stop',default='4u');ap.add_argument('--fast',action='store_true');a=ap.parse_args()
s=(H/'tb/timing_both.scs').read_text()
s=re.sub(r'^VC .*$',f'VPRE (preset 0) vsource dc={a.preset}\nXLF (ctrl vc1 en preset vdd 0) tx_loop_filter rlf={a.r}',s,flags=re.M)
if a.fast:
 s=s.replace('include "cells.scs"','include "cells.scs"\ninclude "loop_filter_v5.scs"')
 s=s.replace(') tx_loop_filter rlf=',') tx_loop_filter_v5 rlf=')
s=s.replace('VE (en 0) vsource dc=1.2','VE (en 0) vsource type=pwl wave=[0 0 400n 0 400.05n 1.2]')
s=s.replace('VO (cpout 0) vsource dc=.6','VO (cpout ctrl) vsource dc=0')
s=re.sub(r'^VRST .*$', 'VRST (rst 0) vsource type=pwl wave=[0 1.2 20n 1.2 20.02n 0]',s,flags=re.M)
s=s.replace('ic vp=1.20001 vn=1.2',f'ic vp=1.20001 vn=1.2 ctrl={a.preset} vc1={a.preset}')
s=re.sub(r'^tran tran .*$',f'ahdl_include "lc_loop_observer.va"\nXOBS (vp vn refb ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer\ntran tran stop={a.stop} maxstep=2p errpreset=conservative strobeperiod=1n strobeoutput=strobeonly',s,flags=re.M)
s=re.sub(r'^save .*$', 'save obsphase obscycles obsctrl obsdivcycles ctrl vc1 hp hn pulse refb en VDD:p VVCO:p VO:p',s,flags=re.M)
(H/'tb'/f'{a.name}.scs').write_text(s)
print(a.name,'preset',a.preset,'V; R',a.r,'; stop',a.stop)
