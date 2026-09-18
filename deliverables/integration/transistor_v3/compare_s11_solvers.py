"""Compare preserved partial solver trials; never treat a cancelled run as pass."""
from pathlib import Path
import json,re
import numpy as np
from analyze_v3 import R,H,parse,cross

def main():
    trials=[('system_config_r2','loop_s11_parallel_tt'),
            ('system_config_gear','loop_s11_gear_tt'),
            ('system_config_moderate','loop_s11_moderate_tt'),
            ('system_config_ax','loop_s11_moderate_tt')]
    rows=[];waves={}
    for run,case in trials:
        p=R/run/case;raw=p/f'{case}.raw'/'tran.tran.tran'
        if not raw.exists():continue
        d=parse(raw)
        if len(d.get('time',[]))<2:continue
        waves[run]=d
        log=(p/'spectre.out').read_text(errors='replace')
        settings=dict(re.findall(r'^\s*(reltol|abstol\(V\)|abstol\(I\)|method|errpreset)\s*=\s*(.*?)\s*$',log,re.M))
        rec=json.loads((p/'result.json').read_text())
        command=rec.get('metadata',{}).get('spectre_command','')
        threads=re.search(r'\+mt=(\d+)',command)
        rows.append(dict(run=run,case=case,last_time_s=float(d['time'][-1]),
            cancelled=(p/'cancellation.json').exists(),
            solver='Spectre X AX' if '+preset=ax' in command else 'APS',
            threads=int(threads.group(1)) if threads else 1,effective_settings=settings,
            enable_rise_ns=(cross(d['time'],d['enable'])*1e9).tolist()))
    comparisons=[]
    if trials[0][0] in waves:
        reference=waves[trials[0][0]]
        for name,d in waves.items():
            if name==trials[0][0]:continue
            limit=min(reference['time'][-1],d['time'][-1])
            t=reference['time'];mask=(t>=100e-9)&(t<=limit)
            comparisons.append(dict(candidate=name,reference=trials[0][0],
                comparison_end_s=float(limit),samples=int(sum(mask)),
                control_max_difference_v=float(np.max(abs(np.interp(t[mask],d['time'],d['ctrl'])-reference['ctrl'][mask]))),
                cycle_control_max_difference_v=float(np.max(abs(np.interp(t[mask],d['time'],d['cycle_ctrl'])-reference['cycle_ctrl'][mask])))))
    result=dict(note='Partial comparisons check numerical sensitivity only. Cancelled trials do not establish final settling.',trials=rows,comparisons=comparisons)
    (H/'results/s11_solver_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
