"""Independent waveform measurements and regression assertions.

Spectre completion alone is never treated as a passing functional test.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
DELIVERY=HERE.parents[2]
ROOT=DELIVERY.parent if DELIVERY.name=='share' and (DELIVERY.parent/'AGENTS.md').exists() else DELIVERY

def crosses(t,y,level=.6,direction=1):
    ix=np.flatnonzero((y[:-1]<level)&(y[1:]>=level)) if direction==1 else np.flatnonzero((y[:-1]>level)&(y[1:]<=level))
    return t[ix]+(level-y[ix])*(t[ix+1]-t[ix])/(y[ix+1]-y[ix])

def clock_stats(t,y,after=0.):
    rise=crosses(t,y);fall=crosses(t,y,direction=-1)
    rise=rise[rise>=after];fall=fall[fall>=after]
    if len(rise)<3:return {'frequency_hz':0,'duty':0,'rises':len(rise)}
    highs=[];periods=[]
    for a,b in zip(rise[:-1],rise[1:]):
        f=fall[(fall>a)&(fall<b)]
        if len(f)==1:highs.append(f[0]-a);periods.append(b-a)
    return {'frequency_hz':float((len(rise)-1)/(rise[-1]-rise[0])),
            'duty':float(sum(highs)/sum(periods)) if periods else None,'rises':len(rise)}

def measure(work):
    rec=json.loads((work/'result.json').read_text(encoding='utf-8'))
    case=rec['case'];checks=[];observed={}
    def check(name,value,limit,passed):checks.append({'name':name,'value':value,'limit':limit,'passed':bool(passed)})
    if not rec['ok']:return {'case':case,'all_passed':False,'errors':rec['errors']}
    data=dict(np.load(work/'waveforms.npz'));t=data['time']
    last={k:float(v[-1]) for k,v in data.items()}
    if case.startswith('top_'):
        k=41 if case=='top_retune' else int(case.split('_')[1][1:])
        target=k*24e6
        ppm=(last['freqout']*1e9/target-1)*1e6
        window=38e-6 if case in ['top_retune','top_k41_recovery'] else 20e-6
        tail=t>window
        maxphase=float(max(abs(data['phaseerr'][tail])))
        maxfreq=float(max(abs(data['fvco'][tail]-data['fvco'][-1]))*1e9)
        track=np.flatnonzero(data['enable']>.6)
        lost=np.flatnonzero((data['enable'][:-1]>.6)&(data['enable'][1:]<.6))
        observed={'k':k,'fout_hz':last['freqout']*1e9,'frequency_error_ppm':ppm,
                  'duty_percent':100*last['dutyout'],'selected_code':last['code'],
                  'final_ctrl_v':last['ctrl'],'phase_sine_max':maxphase,
                  'lock_first_us':float(t[np.flatnonzero(data['locked']>.6)[0]]*1e6) if np.any(data['locked']>.6) else None,
                  'handoff_first_us':float(t[track[0]]*1e6) if len(track) else None,
                  'reacquisitions':len(lost),'counted_output_edges':last['edgecount'],
                  'setup_hold_violations':last['violations'],'track_window_vco_range_hz':maxfreq}
        check('independent output edge frequency',ppm,'abs < 1 ppm',abs(ppm)<1)
        check('settled subsampling phase error',maxphase,'abs sine < .01',maxphase<.01)
        check('qualified frequency and phase lock',last['locked'],'> 0.6 V',last['locked']>.6)
        check('symmetric output duty',last['dutyout'],'0.5 +/- 0.0005 (working functional check)',abs(last['dutyout']-.5)<.0005)
        check('retimer setup/hold monitor',last['violations'],'zero',last['violations']==0)
        check('control compliance in measurement window',[last['vmin'],last['vmax']],'0.2..1.0 V',last['vmin']>=.2 and last['vmax']<=1)
        check('real edges observed',last['edgecount'],'> 100',last['edgecount']>100)
        if case in ['top_retune','top_k41_recovery']:
            check('tracking exits and resumes',len(lost),'>=1',len(lost)>=1)
    elif case=='tb_vco':
        expected=4e9/np.sqrt(1+127/255*((4e9/2.64e9)**2-1))+2e6
        observed=clock_stats(t,data['clk'],1e-9)
        err=observed['frequency_hz']/expected-1
        check('physical VCO edges match equal-C plus fine tuning',err,'abs < 1e-5',abs(err)<1e-5)
        check('differential sinusoidal amplitude',float(max(data['vp']-data['vn'])),'.4 +/- .002 V',abs(max(data['vp']-data['vn'])-.4)<.002)
    elif case=='tb_reference':
        a=crosses(t,data['inp']);b=crosses(t,data['out']);delay=float(np.median(b-a))
        check('reference delay includes half transition',delay,'60 +/- .1 ps',abs(delay-60e-12)<.1e-12)
    elif case=='tb_detector':
        rises=crosses(t,data['pulse']);falls=crosses(t,data['pulse'],direction=-1);refs=crosses(t,data['ref'])
        check('sampled differential voltage',last['sample'],'.2 V',abs(last['sample']-.2)<1e-9)
        widths=falls-rises[:len(falls)]
        check('pulse width',float(np.mean(widths)),'2.083333 ns +/- 1 ps',abs(np.mean(widths)-2.083333333333e-9)<1e-12)
        check('pulse delay',float(np.mean(rises-refs[:len(rises)])),'2.088333 ns +/- 1 ps',abs(np.mean(rises-refs[:len(rises)])-2.088333333333e-9)<1e-12)
    elif case=='tb_cp':
        current=data['VR:p']; mask=data['pulse']>1.19
        check('correct negative feedback pump polarity',float(np.mean(current[mask])),'-24 uA',abs(np.mean(current[mask])+24e-6)<1e-9)
        # Complete single pulse charge, independent numerical integration.
        mask=(t>=0)&(t<30e-9)
        charge=float(np.trapezoid(current[mask],t[mask]))
        check('pump integrated charge',charge,'-50 fC +/- 0.5 fC',abs(charge+50e-15)<.5e-15)
    elif case=='tb_filter':
        error=float(max(abs(data['ctrl']-data['ctrl2'])))
        check('VA filter agrees with independent Spectre primitive R/C',error,'< 1 uV',error<1e-6)
    elif case.startswith('tb_divider_m'):
        m=int(case.split('m')[-1]);observed=clock_stats(t,data['out'],5e-9)
        check('count-based division',observed['frequency_hz'],f'{4e9/m} Hz +/- 10 ppm',abs(observed['frequency_hz']/(4e9/m)-1)<1e-5)
        check('equal high/low half-period',observed['duty'],'.5 +/- .0001',abs(observed['duty']-.5)<.0001)
    elif case.startswith('tb_retimer_'):
        bad=last['violations']
        expected=case.endswith('setup_failure')
        check('setup/hold negative case detected' if expected else 'nominal setup/hold valid',bad,'positive' if expected else 'zero',bad>0 if expected else bad==0)
        observed=clock_stats(t,data['out'],5e-9)
        if not expected:check('retimed edge frequency',observed['frequency_hz'],'1 GHz +/- 10 ppm',abs(observed['frequency_hz']/1e9-1)<1e-5)
    elif case=='tb_output':
        observed=clock_stats(t,data['out'],2e-9)
        check('buffer drives explicit 10 fF behavioral load',observed['frequency_hz'],'1 GHz +/- 10 ppm',abs(observed['frequency_hz']/1e9-1)<1e-5)
        check('logic swing',float(max(data['out'])),'1.2 +/- .001 V',abs(max(data['out'])-1.2)<.001)
    elif case=='tb_bias':check('midpoint reference',last['vmid'],'0.6 V',abs(last['vmid']-.6)<1e-9)
    elif case=='tb_fll':
        check('integer counter frequency',last['measured'],'3.0 GHz +/- .75 MHz',abs(last['measured']-3)<.000751)
        check('zero-error handoff and lock',last['locked'],'>0.6',last['locked']>.6 and last['status']==2)
    elif case=='tb_mainloop':
        from dataclasses import replace
        sys.path.insert(0,str(HERE.parents[1]/'architecture/behavioral_v1'))
        from model import synthesize,sampled_matrices
        cfg=json.loads((HERE.parents[1]/'architecture/behavioral_v1/results/candidate/candidate_B.json').read_text(encoding='utf-8'))
        loop=synthesize(cfg)
        # A 10 ps symmetric pulse transition shifts its centroid by 5 ps.
        loop=replace(loop,delay=loop.delay+5e-12*loop.fs)
        _,_,_,e,b=sampled_matrices(loop)
        mask=(t>1e-9)&(t<5.99e-6)
        ph=np.arcsin(data['phaseerr'][mask]);vc=data['ctrl'][mask];v1=data['vc1'][mask]
        scale=loop.kv/loop.fs
        x=np.array([ph[0],(vc[0]-.6)*scale,(v1[0]-.6)*scale]);pred=[x.copy()]
        fcenter=4e9/np.sqrt(1+6/255*((4e9/2.64e9)**2-1))
        advance=np.array([2*np.pi*(fcenter-3.936e9)/loop.fs,0,0])
        for i in range(len(ph)-1):x=e@x-b*np.sin(x[0])+advance;pred.append(x.copy())
        pred=np.array(pred)
        perr=float(max(abs(pred[:,0]-ph)));verr=float(max(abs(.6+pred[:,1]/scale-vc)))
        check('independent Python state map versus Spectre nonlinear main-loop phase',perr,'< 1e-4 rad',perr<1e-4)
        check('independent Python state map versus Spectre control voltage',verr,'< 10 uV',verr<10e-6)
        observed={'samples':len(ph),'phase_initial_rad':float(ph[0]),'max_phase_difference_rad':perr,'max_control_difference_v':verr}
    else:raise ValueError('No checker for '+case)
    return {'case':case,'raw_path':str(work.relative_to(ROOT)), 'all_passed':all(c['passed'] for c in checks),'checks':checks,'observed':observed}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runs',nargs='+',required=True);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    rows=[]
    for run in args.runs:
        for result in sorted((ROOT/'research/runs/spectre_va'/run).glob('*/result.json')):rows.append(measure(result.parent))
    report={'all_passed':bool(rows) and all(r['all_passed'] for r in rows),'cases':len(rows),'results':rows}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'all_passed':report['all_passed'],'cases':len(rows),'failed':[r for r in rows if not r['all_passed']]},indent=2))
    return 0 if report['all_passed'] else 1

if __name__=='__main__':raise SystemExit(main())
