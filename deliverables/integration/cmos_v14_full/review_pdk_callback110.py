"""Compare completed paired module data, with independent remote evidence."""
from pathlib import Path
import datetime,hashlib,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[4];H=ROOT/'share/deliverables/integration/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def edges(t,y,threshold=0.6,rising=True):
    a=y-threshold
    ii=np.where((a[:-1]<0)&(a[1:]>=0) if rising else (a[:-1]>=0)&(a[1:]<0))[0]
    return t[ii]+(t[ii+1]-t[ii])*(-a[ii])/(a[ii+1]-a[ii])
def stats(t,y,start,end):
    m=(t>=start)&(t<=end);x=y[m];tt=t[m]
    return dict(mean=float(np.trapezoid(x,tt)/(tt[-1]-tt[0])),min=float(x.min()),max=float(x.max()),p2p=float(np.ptp(x)))
def clock(t,y,start,end,threshold=.6):
    r=edges(t,y,threshold);f=edges(t,y,threshold,False)
    r=r[(r>=start)&(r<=end)];f=f[(f>=start)&(f<=end)]
    hz=(len(r)-1)/(r[-1]-r[0]) if len(r)>1 else None
    highs=[float(f[f>x][0]-x) for x in r if len(f[f>x])]
    lows=[float(r[r>x][0]-x) for x in f if len(r[r>x])]
    return dict(frequency_Hz=float(hz) if hz else None,rising_edges=len(r),falling_edges=len(f),min_high_s=min(highs) if highs else None,min_low_s=min(lows) if lows else None,voltage=stats(t,y,start,end))
def main():
    audit1,audit2,out=map(Path,sys.argv[1:]);assert not out.exists()
    audits=[json.loads(p.read_text()) for p in (audit1,audit2)]
    dt=(datetime.datetime.fromisoformat(audits[1]['time'])-datetime.datetime.fromisoformat(audits[0]['time'])).total_seconds();assert dt>=60
    proof=[{j['case']:j for j in a['jobs']} for a in audits]
    protocol=json.loads((H/'results/pdk_callback110_protocol.json').read_text());rows=[]
    for c in protocol['cases']:
        name=c['case'];j=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/name
        for p in proof:
            a=p[name];assert not a['alive'] and a['raw_end'] and a['exit_marker']=='0' and a['remote_inputs_match']
            assert a['final_state_sha256']==sha(j/'final.ic')
            assert a['completed_output_hashes'][name+'.raw/tran.tran.tran']==sha(j/(name+'.raw/tran.tran.tran'))
            assert a['completed_output_hashes']['spectre.out']==sha(j/'spectre.out')
            assert a['effective']['method']=='traponly' and a['effective']['maxstep']==8e-12 and a['effective']['reltol']==.001
        assert proof[0][name]['completed_output_hashes']==proof[1][name]['completed_output_hashes']
        r=json.loads((j/'result.json').read_text());assert r['ok'] and not r['errors'] and r['remote_inputs_match']
        log=(j/'spectre.out').read_text();assert re.search(r'spectre completes with 0 errors',log)
        with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
        t=d['time'];assert len(t)==c['expected_points'] and abs(t[0])<1e-18 and abs(t[-1]-c['stop_s'])<1e-16
        assert np.all(np.diff(t)>0) and all(len(v)==len(t) and np.isfinite(v).all() for v in d.values())
        start={'cpref':50e-9,'rfchain':40e-9,'vco':300e-9}[c['module']];end=c['stop_s']
        metrics=dict(window_s=[start,end],supply_power_W=-1.2*stats(t,d['VDD:p'],start,end)['mean'])
        if c['module']=='cpref':
            ris=edges(t,d['ref']);ros=edges(t,d['refb']);delays=[]
            for x in ris[(ris>=start)&(ris<end-1e-9)]:
                ys=ros[(ros>=x)&(ros<x+1e-9)];assert len(ys)==1;delays.append(float(ys[0]-x))
            metrics.update(reference_delay_mean_s=float(np.mean(delays)),reference_delay_max_s=max(delays),reference=clock(t,d['refb'],start,end),bias=stats(t,d['XCP.nb'],start,end))
            pulse_edges=edges(t,d['pulse']);currents={};charges={}
            for tag,lo,hi in [('positive',60e-9,110e-9),('negative',220e-9,280e-9)]:
                rr=pulse_edges[(pulse_edges>lo)&(pulse_edges<hi)];assert len(rr)==2
                currents[tag]=[stats(t,d['VOUT:p'],x+.5e-9,x+1.5e-9)['mean'] for x in rr]
                charges[tag]=[]
                for x in rr:
                    m=(t>=x)&(t<=x+10e-9);charges[tag].append(float(np.trapezoid(d['VOUT:p'][m],t[m])))
            metrics.update(cp_plateau_current_A={k:float(np.mean(v)) for k,v in currents.items()},cp_10ns_charge_C={k:float(np.mean(v)) for k,v in charges.items()},cp_sample_currents_A=currents)
            metrics['cp_differential_gain_A_per_V']=(metrics['cp_plateau_current_A']['positive']-metrics['cp_plateau_current_A']['negative'])/.02
        else:
            for n in ('clk','data','out'):metrics[n]=clock(t,d[n],start,end)
            a,b=metrics['clk']['frequency_Hz'],metrics['out']['frequency_Hz']
            metrics['divider_ratio']=a/b if a and b else None
            metrics['divide4_observed']=bool(a and b and abs(a/b-4)<.001)
            if c['module']=='vco':
                metrics['rf']=clock(t,d['vp']-d['vn'],start,end,0.)
                metrics['nfilt']=stats(t,d['XV.XL.nfilt'],start,end)
                metrics['nb']=stats(t,d['XV.XL.nb'],start,end)
                metrics['tail']=stats(t,d['XV.XL.tail'],start,end)
                m=(t>=start)&(t<=end);metrics['nfilt_linear_drift_V_per_us']=float(np.polyfit((t[m]-start)*1e6,d['XV.XL.nfilt'][m],1)[0])
        wall=re.findall(r'elapsed time \(wall clock\): ([0-9.eE+]+) s',log)
        rows.append(dict(case=name,module=c['module'],version=c['version'],scope=c['scope'],points=len(t),physical_fields=len(d)-1,units_metadata_excluded=True,metrics=metrics,solver_wall_s=float(wall[-1]) if wall else None,terminal_checks_passed=True,evidence=dict(audit_sha256=[sha(audit1),sha(audit2)],raw_sha256=sha(j/(name+'.raw/tran.tran.tran')),log_sha256=sha(j/'spectre.out'),final_ic_sha256=sha(j/'final.ic'),waveform_sha256=sha(j/'waveforms.npz'),inputs_sha256=r['inputs_sha256'])))
    comparisons={}
    for module in ('cpref','rfchain','vco'):
        pair={r['version']:r['metrics'] for r in rows if r['module']==module}
        def flat(d,p=''):
            ans={}
            for k,v in d.items():
                if isinstance(v,dict):ans.update(flat(v,p+k+'.'))
                elif isinstance(v,(int,float)) and not isinstance(v,bool):ans[p+k]=v
            return ans
        a,b=map(flat,(pair['before'],pair['after']))
        comparisons[module]={k:dict(before=a[k],after=b[k],delta=b[k]-a[k],relative_percent=100*(b[k]/a[k]-1) if a[k] else None) for k in a if k in b}
    out.write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),stable_terminal_interval_s=dt,cases=rows,comparisons=comparisons,boundaries=['Local module results, not full PLL lock or full-range verification','400ns warm-bias VCO is not asymptotic steady state','No transient noise; frequency or propagation differences are not jitter','Callback values use PDK pre-layout defaults; no fabricated well distance or PEX','Original running recenter109 simulation and adopted baseline were not modified']),indent=2)+'\n')
    print(json.dumps({m:{k:v for k,v in d.items() if k in ['supply_power_W','reference_delay_mean_s','cp_differential_gain_A_per_V','rf.frequency_Hz','out.frequency_Hz','nfilt.mean','divider_ratio']} for m,d in comparisons.items()},indent=2))
if __name__=='__main__':main()
