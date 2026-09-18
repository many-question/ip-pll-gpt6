from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
MODEL='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
def head(corner='tt',temp=27):return f'''simulator lang=spectre
global 0
include "{MODEL}" section={corner}
include "{MODEL}" section=stat_noise
simulator lang=spectre insensitive=no
include "cells.scs"
include "receiver.scs"
simulatorOptions options reltol=1e-5 vabstol=1e-7 iabstol=1e-13 temp={temp}
'''
def main():
    params=[(n,p,b) for n in [2,4,8] for p in [.3,.6,1.2] for b in [5,15]]
    for corner,temp in [('ss',60),('tt',27)]:
        lines=[head(corner,temp),'VP (ip 0) vsource type=sine dc=1.05 ampl=.08 freq=2G','VN (in 0) vsource type=sine dc=1.05 ampl=.08 freq=2G sinephase=180']
        save=[]
        for i,(n,p,b) in enumerate(params):
            lines += [f'VS{i} (vdd{i} 0) vsource dc=1.2',f'X{i} (ip in op{i} on{i} vdd{i} 0) tx_regen_receiver wn={n}u wp={p}u ibias={b}u',f'C{i} (op{i} 0) capacitor c=20f',f'D{i} (on{i} 0) capacitor c=20f']
            save += [f'op{i}',f'on{i}',f'VS{i}:p']
        lines+=['tran tran stop=100n maxstep=5p errpreset=conservative','save '+' '.join(save),'saveOptions options save=selected']
        (HERE/'tb'/f'tb_receiver_grid_{corner}.scs').write_text('\n'.join(lines)+'\n')
    (HERE/'results/receiver_grid_parameters.json').write_text(json.dumps(params,indent=2)+'\n')
if __name__=='__main__':main()
