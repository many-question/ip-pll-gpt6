"""Evidence screens for physical V14 integration; partial live data are excluded."""
from pathlib import Path
import json, re
import numpy as np
H=Path(__file__).resolve().parent
ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'

def cross(t,v,level=.6):
    i=np.flatnonzero((v[:-1]<level)&(v[1:]>=level))
    return t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])

def logic_windows(d):
    rows=[]
    for tns,expected in [(150,False),(500,True),(700,False),(900,False),(1100,True),(1700,False)]:
        mask=abs(d['time']-tns*1e-9)<10e-9
        vals={k:[float(min(d[k][mask])),float(max(d[k][mask]))] for k in ['amp_good','phase_good']}
        ok=vals['phase_good'][0]>1 if expected else vals['phase_good'][1]<.2
        amp_expected=200<tns<1200
        ok=ok and (vals['amp_good'][0]>1 if amp_expected else vals['amp_good'][1]<.2)
        rows.append(dict(center_ns=tns,expected_phase_good=expected,expected_amp_good=amp_expected,ranges_v=vals,passed=ok))
    return dict(windows=rows,passed=all(x['passed'] for x in rows),scope='Ideal RF and held sample stimuli; deterministic detector function only, no noise/offset/MC qualification.')

def divider(d,m):
    t=d['time'];edges=cross(t,d['data']);rf=cross(t,d['clk']);fr=1/np.mean(np.diff(rf))
    fo=1/np.mean(np.diff(edges)) if len(edges)>2 else 0
    err=float(max(abs(np.diff(edges)*fr/m-1))) if len(edges)>2 else None
    cycles=[]
    for a,b in zip(edges[:-1],edges[1:]):
        v=d['data'][(t>=a)&(t<=b)]
        cycles.append(float(min(v))<.2 and float(max(v))>1)
    falling=cross(t,1.2-d['data']);duties=[]
    for a,b in zip(edges[:-1],edges[1:]):
        f=falling[(falling>a)&(falling<b)]
        if len(f)==1:duties.append(float((f[0]-a)/(b-a)))
    return dict(m=m,rf_mhz=float(fr/1e6),output_mhz=float(fo/1e6),edges=len(edges),max_period_error=err,
                duty_mean_percent=float(100*np.mean(duties)) if duties else None,
                duty_range_percent=[float(100*min(duties)),float(100*max(duties))] if duties else None,
                every_cycle_full_swing=bool(cycles and all(cycles)),passed=bool(len(edges)>5 and abs(fo*m/fr-1)<.001 and err<.02 and all(cycles)),
                power_mw=float(-1.2*np.trapezoid(d['VDD:p'],t)/(t[-1]-t[0])*1e3),
                scope='Ideal 20ps rail clock, 1.2V, 10fF, final40ns. No RF interface or retimer; not PLL power.')

def loop(d):
    t=d['time'];ix=np.flatnonzero(np.diff(d['obsphase'])!=0)+1
    ix=ix[t[ix]>t[-1]-1e-6];tt=t[ix];p=np.unwrap(d['obsphase'][ix])
    if len(ix)<3:return dict(passed=False,reason='Insufficient observer samples')
    vals=dict(phase_pp_rad=float(np.ptp(p)),phase_drift_rad_per_us=float(np.polyfit((tt-tt[0])*1e6,p,1)[0]),
              max_rf_cycles_error=float(max(abs(d['obscycles'][ix]-164))),max_out_cycles_error=float(max(abs(d['obsdivcycles'][ix]-41))),
              mean_output_mhz=float(np.mean(d['obsdivcycles'][ix])*24),ctrl_range_v=[float(min(d['obsctrl'][ix])),float(max(d['obsctrl'][ix]))])
    vals['passed']=bool(vals['phase_pp_rad']<.02 and abs(vals['phase_drift_rad_per_us'])<.01 and vals['max_rf_cycles_error']<.001 and vals['max_out_cycles_error']<.001 and .2<vals['ctrl_range_v'][0]<=vals['ctrl_range_v'][1]<1)
    vals['criteria']='Last1us: phase pp<.02rad, drift<.01rad/us, cycles/ref errors<.001, ctrl0.2..1V; functional stationarity, not jitter.'
    vals['measurement_limit']='Sparse GHz voltage/current samples are not used for RF swing or average power.'
    vals['end_us']=float(t[-1]*1e6)
    vals['final_state']={k:float(d[k][-1]) for k in ['cfg_ready','qualified','range_error','frequency_good','phase_good','amp_good','XP.en','XP.XC.acquired','XV.XL.nb','XP.XV.XL.nb'] if k in d}
    if 'energy_nj' in d:
        first=int(np.searchsorted(t,t[-1]-1e-6))
        vals['final_1us_total_supply_power_mw']=float((d['energy_nj'][-1]-d['energy_nj'][first])/((t[-1]-t[first])*1e6))
        vals['power_method']='Internal-timestep integration of complete external1.2V supply; power=delta(nJ)/delta(us). Does not assume sparse sampled current is accurate.'
        vals['whole_run_energy_nj']=float(d['energy_nj'][-1]-d['energy_nj'][0])
    if 'XP.XC.phase_held' in d:
        vals['final_1us_phase_held_high_fraction']=float(np.mean(d['XP.XC.phase_held'][t>t[-1]-1e-6]>.6))
    if 'qualified' in d:
        vals['final_1us_qualified_high_fraction']=float(np.mean(d['qualified'][t>t[-1]-1e-6]>.6))
        edges=cross(t,d['qualified'])
        vals['first_qualified_us']=float(edges[0]*1e6) if len(edges) else None
    return vals

def phase_timing(d):
    t=d['time'];fall=cross(t,1.2-d['ref']);rise=cross(t,d['ref']);rows=[]
    for edge in fall[fall>200e-9]:
        if edge+4e-9>t[-1]:continue
        i=int(np.argmin(abs(t-(edge-2e-9))))
        j=int(np.argmin(abs(t-(edge+4e-9))))
        margins=[float(d['hp'][i]-d['XDET.wl'][i]),float(d['XDET.wh'][i]-d['hp'][i])]
        expected=all(x>0 for x in margins)
        ambiguous=min(abs(x) for x in margins)<.005
        actual=bool(d['phase_held'][j]>.6)
        before=rise[rise<edge][-1];k=int(np.argmin(abs(t-(before-.2e-9))))
        rows.append(dict(falling_edge_ns=float(edge*1e9),window_margins_v=margins,
                         expected_window=expected,ambiguous=ambiguous,held_after_fall=actual,
                         raw_before_rise=bool(d['phase_good'][k]>.6),passed=None if ambiguous else bool(actual==expected)))
    decisive=[x for x in rows if not x['ambiguous']]
    return dict(rows=rows,passed=all(x['passed'] for x in decisive) if decisive else None,
                inconclusive_rows=sum(x['ambiguous'] for x in rows),
                scope='Actual sampler/comparator/resettable FF with ideal3.936GHz RF and24MHz reference; sample window2ns before fall, FF4ns after fall,5mV threshold ambiguity guard. Not mismatch/noise signoff.')

def main():
    rows=[]
    for rp in sorted(R.glob('*/*/result.json')):
        rec=json.loads(rp.read_text());job=rp.parent
        if not rec.get('remote_inputs_match') or not (job/'waveforms.npz').exists():continue
        log=(job/'spectre.out').read_text(errors='replace')
        row=dict(run=job.parent.name,case=job.name,simulator_completed=bool(re.search(r'spectre completes with 0 errors',log)),
                 cancelled=(job/'cancellation.json').exists(),
                 warnings=[x.strip() for x in log.splitlines() if 'WARNING (' in x],
                 errors=[x.strip() for x in log.splitlines() if 'ERROR (' in x],
                 input_hashes_verified=rec['remote_inputs_match'],source_result=str(rp.relative_to(ROOT)))
        # Bridge's coarse classifier reports "convergence failure" when a successful
        # log discusses DC fallback. Actual Spectre final status and ERROR lines govern.
        with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
        if job.name.startswith('detector_'):row['detector']=logic_windows(d)
        if job.name.startswith('phasehold_'):row['phase_timing']=phase_timing(d)
        if mt:=re.fullmatch(r'bank(?:\d*|tree|rt)_m(\d+)_(tt|ss|ff)',job.name):
            row['divider']=divider(d,int(mt[1]))
            if job.name.startswith('bankrt_'):
                row['divider']['scope']='Ideal20ps rail RF clock; full six-mode bank plus retimer and10fF. Includes RF/4 acquisition buffer, no analog RF interface. Final40ns.'
                acq=cross(d['time'],d['acqclk']);row['divider']['acq_mhz']=float(1e-6/np.mean(np.diff(acq))) if len(acq)>2 else None
        if 'obsphase' in d:
            row['loop']=loop(d)
            if row['cancelled']:
                row['loop']['passed']=False
                row['loop']['reason']='Deliberately stopped diagnostic; partial time window is not accepted.'
        if job.name.startswith('bias_lc') or job.name.startswith('bias2500'):
            t=d['time'];e=cross(t,d['vp']-d['vn'],0);o=cross(t,d['out'])
            row['bias_lc']=dict(rf_mhz=float(1e-6/np.mean(np.diff(e))),out_mhz=float(1e-6/np.mean(np.diff(o))),
                    power_mw=float(-1.2*np.trapezoid(d['VDD:p'],t)/(t[-1]-t[0])*1e3),bias_v=float(np.mean(d['XV.XL.nb'])),
                    scope='Fixed-code, fixed-control loaded oscillator fixture; no FLL/control, not full PLL power.')
        rows.append(row)
    (H/'results/validation.json').write_text(json.dumps(rows,indent=2)+'\n')
    for r in rows:
        print(r['run'],r['case'],{k:v.get('passed',v) for k,v in r.items() if k in ['loop','divider','detector','bias_lc','phase_timing']})

if __name__=='__main__':main()
