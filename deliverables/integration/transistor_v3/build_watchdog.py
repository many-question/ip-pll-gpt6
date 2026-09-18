from pathlib import Path
import json,sys,subprocess,re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/transistor_v3'
sys.path.insert(0,str(H))
from build_control import ROOT,MAP
from build_control_tb import base,signal,T

def main():
    name='frequency_watchdog';out=B/(name+'_mapped.json')
    command=f'read_verilog "{B.as_posix()}/{name}.v"; hierarchy -top {name}; proc; flatten; opt; techmap; opt; dffunmap; opt_clean; write_json "{out.as_posix()}"'
    import shutil
    local=ROOT/'research/run_yosys.py'
    entry=[sys.executable,str(local)] if local.exists() else [shutil.which('yosys') or shutil.which('yowasp-yosys') or 'yowasp-yosys']
    p=subprocess.run(entry+['-p',command],capture_output=True,text=True)
    (ROOT/'research/frequency_watchdog_synthesis.log').write_text(p.stdout+p.stderr)
    assert p.returncode==0,p.stderr
    mod=json.loads(out.read_text())['modules'][name];names={};ports=[]
    for n,info in mod['ports'].items():
        for i,b in enumerate(info['bits']):
            port=n if len(info['bits'])==1 else f'{n}{i}'
            names[b]=port;ports.append(port)
    def node(b):return {'0':'vss','1':'vdd'}.get(b,names.get(b,f'n{b}'))
    lines=['simulator lang=spectre',f'// {len(mod["cells"])} project-owned generic cells mapped to MOS.',
           'subckt tx_frequency_watchdog ('+' '.join(ports)+' vdd vss)']
    for i,(_,c) in enumerate(sorted(mod['cells'].items())):
        sub,order=MAP[c['type']];nets=' '.join(node(c['connections'][n][0]) for n in order)
        lines.append(f'X{i} ({nets} vdd vss) {sub}')
    lines.append('ends tx_frequency_watchdog')
    (B/(name+'.scs')).write_text('\n'.join(lines)+'\n')
    trials=[(41,1312),(41,1311),(41,1313),(41,1310),(41,1314),(14,448),(9,288),(9,0),(41,16383),(8,256),(42,1344)]
    schedule=[dict(time_s=200e-9+2e-6*i,k=k,measured=m,expected=9<=k<=41 and abs(m-32*k)<=1) for i,(k,m) in enumerate(trials)]
    (H/'results/watchdog_stimulus.json').write_text(json.dumps(dict(cells=len(mod['cells']),cases=schedule),indent=2)+'\n')
    for corner,temp in [('tt',27),('ss',60),('ff',0)]:
        s=base(corner,temp)+['include "frequency_watchdog.scs"']
        s+=[signal('active',[(t,v) for x in schedule for t,v in [(x['time_s'],1),(x['time_s']+1.75e-6,0)]])]
        for j in range(6):s.append(signal(f'target_k{j}',[(x['time_s']-50e-9,(x['k']>>j)&1) for x in schedule]))
        for j in range(14):s.append(signal(f'measured{j}',[(x['time_s']-50e-9,(x['measured']>>j)&1) for x in schedule]))
        s+=['XD ('+' '.join(ports)+' vdd 0) tx_frequency_watchdog']
        for n in ['count_gate','count_reset','frequency_good','valid']:s.append(f'C{n} ({n} 0) capacitor c=20f')
        s+=['tran tran stop=22.2u maxstep=2n method=gear2only errpreset=moderate strobeperiod=1n strobeoutput=strobeonly',
            'save '+' '.join(ports)+' VDD:p','saveOptions options save=selected']
        (H/'tb'/f'tb_watchdog_{corner}.scs').write_text('\n'.join(s)+'\n')
    s=base('tt',27)+['include "frequency_watchdog.scs"',signal('active',[(200e-9,1),(25e-6,0)])]
    for j in range(6):s.append(f'VK{j} (target_k{j} 0) vsource dc={1.2 if 41&(1<<j) else 0}')
    for j in range(14):s.append(signal(f'measured{j}',[(200e-9,(1312>>j)&1),(10e-6,(1316>>j)&1),(20e-6,(1312>>j)&1)]))
    s+=['XD ('+' '.join(ports)+' vdd 0) tx_frequency_watchdog',
        'tran tran stop=25.5u maxstep=2n method=gear2only errpreset=moderate strobeperiod=1n strobeoutput=strobeonly',
        'save '+' '.join(ports)+' VDD:p','saveOptions options save=selected']
    (H/'tb/tb_watchdog_repeat_tt.scs').write_text('\n'.join(s)+'\n')
    # Actual 984 MHz counter/snapshot integration at TT. First full window.
    s=base('tt',27)+['include "frequency_watchdog.scs"','include "fll_circuit.scs"',signal('active',[(200e-9,1)]),
        'VCLK (clk 0) vsource type=pulse val0=0 val1=1.2 period=1.01626016260163n width=.4881300813n rise=20p fall=20p delay=3n']
    for j in range(6):s.append(f'VK{j} (target_k{j} 0) vsource dc={1.2 if 41&(1<<j) else 0}')
    s+=['XD ('+' '.join(ports)+' vdd 0) tx_frequency_watchdog',
        'XC (clk count_gate count_reset '+' '.join(f'q{i}' for i in range(14))+' vdd 0) tx_fll_counter',
        'XS (count_gate '+' '.join(f'q{i}' for i in range(14))+' '+' '.join(f'measured{i}' for i in range(14))+' vdd 0) tx_fll_snapshot',
        'tran tran stop=2.1u maxstep=100p method=gear2only errpreset=moderate strobeperiod=200p strobeoutput=strobeonly',
        'save '+' '.join(ports)+' '+' '.join(f'q{i}' for i in range(14))+' XC.gclk VDD:p','saveOptions options save=selected']
    (H/'tb/tb_watchdog_counter_tt.scs').write_text('\n'.join(s)+'\n')
    for label,freq in [('nom',216e6),('harm_hi',216e6+24e6/14),('harm_lo',216e6-24e6/14)]:
        t='\n'.join(s)+'\n'
        t=re.sub(r'VCLK .*\n',f'VCLK (clk 0) vsource type=pulse val0=0 val1=1.2 period={1/freq:.15g} width={.5/freq-20e-12:.15g} rise=20p fall=20p delay=3n\n',t)
        for j in range(6):t=re.sub(rf'VK{j} .*\n',f'VK{j} (target_k{j} 0) vsource dc={1.2 if 9&(1<<j) else 0}\n',t)
        (H/'tb'/f'tb_watchdog_counter_{label}.scs').write_text(t)
    print('MOS generic cells',len(mod['cells']))
if __name__=='__main__':main()
