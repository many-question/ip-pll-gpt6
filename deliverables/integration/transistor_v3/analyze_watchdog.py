from pathlib import Path
import json
import numpy as np
from analyze_v3 import H,get,word,cross,power

def main():
    schedule=json.loads((H/'results/watchdog_stimulus.json').read_text())['cases']
    result=dict(logic=[],counter=[],repeat=None,frontend=None)
    for corner in ['tt','ss','ff']:
        d=get('watchdog_logic',f'tb_watchdog_{corner}')
        if d is None:continue
        t=d['time'];rows=[]
        for x in schedule:
            i=np.argmin(abs(t-(x['time_s']+1.65e-6)))
            j=np.argmin(abs(t-(x['time_s']+1.9e-6)))
            good=bool(d['frequency_good'][i]>.6)
            cleared=d['frequency_good'][j]<.3 and d['count_gate'][j]<.3 and d['count_reset'][j]>.9
            rows.append(dict(**x,observed=good,pass_check=bool(good==x['expected'] and cleared)))
        rises=cross(t,d['count_gate']);falls=cross(t,d['count_gate'],up=False)
        widths=[float(falls[falls>r][0]-r) for r in rises if np.any(falls>r)]
        result['logic'].append(dict(corner=corner,checks=rows,gate_widths_s=widths,pass_check=bool(all(x['pass_check'] for x in rows) and len(widths)==len(schedule) and max(abs(np.array(widths)-32/24e6))<2e-9),power_mw=power(d,2e-6)))
    cases=[('watchdog_counter','tb_watchdog_counter_tt',41,True),('watchdog_harmonic','tb_watchdog_counter_nom',9,True),('watchdog_harmonic','tb_watchdog_counter_harm_hi',9,False),('watchdog_harmonic','tb_watchdog_counter_harm_lo',9,False)]
    for run,case,k,expected in cases:
        d=get(run,case)
        if d is None:continue
        t=d['time'];valid=cross(t,d['valid']);assert len(valid)==1
        i=np.searchsorted(t,valid[0]+15e-9)
        count=int(word(d,'measured',14)[i]);observed=bool(d['frequency_good'][i]>.6)
        edges=cross(t,d['XC.gclk']);edges=edges[edges<valid[0]]
        result['counter'].append(dict(case=case,k=k,count=count,edge_count=len(edges),expected_good=expected,observed_good=observed,pass_check=bool(count==len(edges) and observed==expected and (abs(count-32*k)<=1)==expected)))
    d=get('watchdog_repeat','tb_watchdog_repeat_tt')
    if d is not None:
        t=d['time'];valid=cross(t,d['valid']);ii=np.searchsorted(t,valid+15e-9)
        states=(d['frequency_good'][ii]>.6).tolist();spacing=np.diff(valid)
        result['repeat']=dict(valid_times_s=valid.tolist(),frequency_good=states,pass_check=bool(states==[True,False,True] and np.max(abs(spacing-256/24e6))<2e-9 and d['frequency_good'][-1]<.3 and d['count_gate'][-1]<.3 and d['count_reset'][-1]>.9))
    d=get('monitored_frontend','tb_monitored_frontend_tt')
    if d is not None:
        t=d['time'];count=word(d,'XC.q',14);reset_release=cross(t,d['count_reset'],up=False)[-1]
        edges=cross(t,d['XC.XCOUNT.gclk']);edges=edges[edges>reset_release]
        safe=all(float(np.max(d[n]))<.3 for n in ['enable','pulse','qualified','range_error','config_invalid','restart','frequency_good'])
        result['frontend']=dict(final_count=int(count[-1]),edge_count=len(edges),pass_check=bool(safe and count[-1]==len(edges) and len(edges)>100 and np.ptp(count[t>1.3e-6])==0 and d['config_ready'][-1]>.9),power_mw=power(d,1e-6))
    (H/'results/watchdog_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
