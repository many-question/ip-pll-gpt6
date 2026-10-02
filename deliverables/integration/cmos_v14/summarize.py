"""Summarize every trial and apply extra cycle-by-cycle checks to passing points."""
import csv,json
from pathlib import Path
import numpy as np
from analyze import H,R,cross

def main():
    rows=json.loads((H/'results/validation.json').read_text());out=[]
    for row in rows:
        w=row.get('wave',{});s=w.get('signals',{})
        out.append(dict(case=row['case'],run=row['run'],sim_ok=row['sim_ok'],pass_function=w.get('pass_function',False),
            rf_mhz=s.get('rf',{}).get('frequency_hz',0)/1e6,out_mhz=s.get('out',{}).get('frequency_hz',0)/1e6,
            power_mw=w.get('power_mw',{}).get('VDD:p'),clk_min_v=s.get('clk',{}).get('range_v',[None,None])[0],clk_max_v=s.get('clk',{}).get('range_v',[None,None])[1]))
    with (H/'results/cases.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=out[0].keys());wr.writeheader();wr.writerows(out)
    checks=[]
    for row in rows:
        if not row.get('wave',{}).get('pass_function'):continue
        job=R/row['run']/row['case']
        with np.load(job/'waveforms.npz') as z:d=dict(z)
        t=d['time'];nodes={}
        for k in ['clk','q1','data','out']:
            v=d[k];e=cross(t,v,.6);mins=[];maxs=[]
            for a,b in zip(e[:-1],e[1:]):
                vv=v[(t>=a)&(t<b)];mins.append(float(min(vv)));maxs.append(float(max(vv)))
            nodes[k]=dict(complete_cycles=len(mins),worst_low_v=max(mins) if mins else None,
                          worst_high_v=min(maxs) if maxs else None,
                          pass_every_cycle_rails=bool(len(mins)>0 and max(mins)<.2 and min(maxs)>1),
                          fraction_above_0p6=float(np.trapezoid((v>.6).astype(float),t)/(t[-1]-t[0])))
        checks.append(dict(case=row['case'],run=row['run'],nodes=nodes,
                           pass_complete_cycle_rails=all(n['pass_every_cycle_rails'] for n in nodes.values())))
    indexed={r['case']:r for r in rows};prec=[]
    for fine in rows:
        if not fine['case'].endswith('_fine'):continue
        base=indexed.get(fine['case'][:-5]);
        if not base or 'wave' not in base or 'wave' not in fine:continue
        a=base['wave'];b=fine['wave'];df=b['reference_RF_frequency_hz']/a['reference_RF_frequency_hz']-1
        dp=b['power_mw']['VDD:p']/a['power_mw']['VDD:p']-1
        prec.append(dict(base=base['case'],fine=fine['case'],relative_rf_change=df,relative_power_change=dp,
            pass_precision=bool(a['pass_function'] and b['pass_function'] and abs(df)<.001 and abs(dp)<.01)))
    summary=dict(total_runs=len(rows),simulator_normal=sum(r['sim_ok'] for r in rows),
        functional_pass=sum(r.get('wave',{}).get('pass_function',False) for r in rows),
        actual_lc=[r for r in rows if r['case'].startswith('lc_')],precision=prec,cycle_checks=checks,
        scope='CMOS /4 SS diagnostic and conditional functional repair. Fixed-control actual Q5 LC includes reference/sampler/CP; not locked PLL. No new noise result.',
        remaining=['Full-power <=4mW including omitted circuitry','PVT/frequency/reset/hold and6modes','Noise regression and actualPLLnoise','PEX/area/reliability and inductorPDK/EM'])
    (H/'results/summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print('Runs',len(rows),'normal',summary['simulator_normal'],'functional',summary['functional_pass'])
    print('Precision',prec)
    print('Complete-cycle checks',[(r['case'],r['pass_complete_cycle_rails']) for r in checks])

if __name__=='__main__':main()
