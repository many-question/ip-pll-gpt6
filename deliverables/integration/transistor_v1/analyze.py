"""Independent measurements. Characterization and failed designs are retained.

No requirement on duty tolerance is invented (DEC-0003). No transient edge
variation is reported as band-integrated random jitter.
"""
import argparse,hashlib,json,sys,importlib.util,re
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
DELIVERY=HERE.parents[2]
ROOT=DELIVERY.parent if DELIVERY.name=='share' and (DELIVERY.parent/'AGENTS.md').exists() else DELIVERY
spec=importlib.util.spec_from_file_location('va_metrics',HERE.parent/'va_v1/analyze.py')
va_metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(va_metrics)
crosses,clock_stats=va_metrics.crosses,va_metrics.clock_stats

def average(t,y,lo,hi):
    m=(t>lo)&(t<hi);x=np.r_[lo,t[m],hi];v=np.interp(x,t,y)
    return float(np.trapezoid(v,x)/(hi-lo))

def measure(path):
    rec=json.loads(path.read_text(encoding='utf-8'));case=rec['case'];work=path.parent
    out={'case':case,'run':work.parent.name,'raw_path':work.relative_to(ROOT).as_posix(),
         'execution_ok':rec['ok'],'remote_inputs_match':rec.get('remote_inputs_match',False),
         'source_inputs_sha256':rec['inputs_sha256'],'measurements':{},'checks':[]}
    def check(name,passed,value,limit):out['checks'].append({'name':name,'passed':bool(passed),'value':value,'limit':limit})
    check('immutable input audit',out['remote_inputs_match'],out['remote_inputs_match'],'true')
    bad_inputs=[]
    for name,expected in rec['inputs_sha256'].items():
        src=work/'inputs'/name
        if not src.exists() or hashlib.sha256(src.read_bytes()).hexdigest()!=expected:bad_inputs.append(name)
    check('local input snapshots match recorded hashes',not bad_inputs,bad_inputs,'all frozen local inputs intact')
    if not rec['ok'] or not (work/'waveforms.npz').exists():
        out.update(outcome='execution_incomplete',errors=rec['errors']);return out
    log=work/'spectre.out'
    if not log.exists():log=work/'spectre_recovered.out'
    zero_errors=log.exists() and bool(re.search(r'spectre completes with 0 errors',log.read_text(errors='replace'),re.I))
    check('Spectre completed with zero errors',zero_errors,bool(zero_errors),'completed log states 0 errors; notices are not errors')
    d=dict(np.load(work/'waveforms.npz'));t=d['time'];m=out['measurements']
    check('finite increasing saved time',np.all(np.isfinite(t)) and np.all(np.diff(t)>0),[float(t[0]),float(t[-1])],'finite and strictly increasing')
    bad_signals=[name for name,values in d.items() if not np.all(np.isfinite(values))]
    check('finite saved signals',not bad_signals,bad_signals,'no NaN or infinity in any saved signal')
    net=(work/'inputs'/f'{case}.scs').read_text(encoding='utf-8')
    stop_token=re.search(r'tran\s+tran\s+stop=([\deE.+-]+[munpf]?)',net).group(1)
    match=re.fullmatch(r'([\deE.+-]+)([munpf]?)',stop_token)
    requested=float(match[1])*{'':1.,'m':1e-3,'u':1e-6,'n':1e-9,'p':1e-12,'f':1e-15}[match[2]]
    check('requested transient completed',abs(t[-1]-requested)<max(1e-15,requested*1e-8),float(t[-1]),requested)
    m['stop_s']=float(t[-1])
    if 'VDD:p' in d:
        m['supply_average_mw']=-1200*average(t,d['VDD:p'],t[-1]/2,t[-1])
        m['power_window_s']=[float(t[-1]/2),float(t[-1])]
    if 'power_mw' in d:m['integrated_realized_supply_mw']=float(d['power_mw'][-1])
    is_loop=case.startswith(('loop_','top_','probe_'))
    if is_loop:
        for k in ['freqout','dutyout','ctrl','vc1','sample','phaseerr','locked','vmin','vmax','code','edgecount']:
            if k in d:m[k]=float(d[k][-1])
        m['output_frequency_hz']=m['freqout']*1e9
        m['frequency_error_ppm']=(m['output_frequency_hz']/984e6-1)*1e6
        tail=t>t[-1]-.5e-6 if t[-1]>1e-6 else t>t[-1]*.6
        m['tail_ctrl_pp_v']=float(np.ptp(d['ctrl'][tail]))
        if 'cycle_ctrl' in d:
            m['tail_cycle_ctrl_pp_v']=float(np.ptp(d['cycle_ctrl'][tail]))
            m['tail_cycle_vc1_pp_v']=float(np.ptp(d['cycle_vc1'][tail]))
        # Saved sample is only valid while the physical sampler is holding.
        # The VA adapter initially exposed tracking portions too; assess output
        # frequency/control and the FLL's edge-qualified lock separately.
        if not case.startswith('probe_'):
            check('output frequency',abs(m['frequency_error_ppm'])<1,m['frequency_error_ppm'],'abs < 1 ppm')
            check('control operating interval',m['vmin']>.2 and m['vmax']<1,[m['vmin'],m['vmax']],'0.2..1.0 V')
            settling=m.get('tail_cycle_ctrl_pp_v',m['tail_ctrl_pp_v'])
            check('settled control',settling<.001,settling,'< 1 mV over final 0.5 us; reference-phase samples when observer present; raw ripple reported separately')
            if case.startswith('top_'):check('FLL qualified lock',m.get('locked',0)>.6,m.get('locked',0),'> .6 V')
            if 'fll_sample' in d:
                m['valid_held_sample_max_v']=float(max(abs(d['fll_sample'][tail])))
                check('valid held error settled',m['valid_held_sample_max_v']<.004,m['valid_held_sample_max_v'],'abs < 4 mV')
        if 'locked' in d and np.any(d['locked']>.6):m['first_lock_us']=float(t[np.flatnonzero(d['locked']>.6)[0]]*1e6)
    elif case.startswith(('tb_reference_','tb_output_','tb_retimer_','tb_c2mos_','tb_tspc_','tb_div2_')):
        signal='q' if case.startswith('tb_div2_') else 'out'
        m.update(clock_stats(t,d[signal],1e-9 if 'reference' in case else 5e-9))
        m['duty_percent']=None if m['duty'] is None else 100*m['duty']
        if 'pattern' in case:
            clk=crosses(t,d['clk'],direction=-1);latencies=[]
            for direction in [1,-1]:
                a=crosses(t,d['data'],direction=direction);b=crosses(t,d['out'],direction=direction)
                a=a[a>2e-9];b=b[b>2e-9]
                check(f'edge conservation direction {direction}',len(a)==len(b),[len(a),len(b)],'equal input and output transition counts')
                if len(a)==len(b):
                    capture=np.array([clk[clk>x][0] for x in a]);dt=b-capture;latencies.extend(dt)
                    check(f'causal capture direction {direction}',np.all((dt>0)&(dt<400e-12)),[float(min(dt)*1e12),float(max(dt)*1e12)],'0..400 ps; shorter than minimum 500 ps data dwell')
            if latencies:m['capture_latency_ps']=[float(min(latencies)*1e12),float(max(latencies)*1e12)]
        else:
            f=24e6 if 'reference' in case else 984e6 if 'output' in case else 2e9 if 'div2' in case else 1e9
            err=(m['frequency_hz']/f-1)*1e6
            check('correct output frequency',abs(err)<10,err,'abs < 10 ppm')
        if 'inp' in d:
            for direction,key in [(1,'rise_delay_ps'),(-1,'fall_delay_ps')]:
                a=crosses(t,d['inp'],direction=direction);b=crosses(t,d['out'],direction=direction)
                if len(a)==len(b):m[key]=float(np.median(b-a)*1e12)
    elif case=='tb_cml_grid':
        rows=[]
        for i,(rload,ibias) in enumerate((r,b) for r in [1600,2000,2400] for b in [20,30,40]):
            x=d[f'qp{i}']-d[f'qn{i}'];edges=crosses(t,x,level=0);edges=edges[edges>30e-9];amp=float(np.ptp(x[t>30e-9])/2)
            freq=(len(edges)-1)/(edges[-1]-edges[0]) if len(edges)>2 and amp>.01 else 0.
            rows.append({'rload_ohm':rload,'ibias_ua':ibias,'frequency_hz':float(freq),'amplitude_v':amp,'power_mw':-1200*average(t,d[f'VS{i}:p'],30e-9,50e-9)})
        m['grid']=rows
    elif case.startswith(('tb_cml_div2_','tb_cml_cmos_')):
        x=d['qp']-d['qn'];r=crosses(t,x,level=0);cut=max(10e-9,t[-1]/2);r=r[r>cut];tail=t>cut
        f=(len(r)-1)/(r[-1]-r[0]) if len(r)>2 else 0.
        if np.ptp(x[tail])<.02:f=0. # Suppress meaningless crossings of roundoff-level differential voltage.
        m.update(frequency_hz=float(f),differential_peak_v=float(np.ptp(x[tail])/2))
        target=1.344e9 if 'lowamp' in case else 2e9
        check('correct divide by two',abs(f/target-1)<1e-5,f,f'{target} Hz +/- 10 ppm')
        check('usable differential amplitude',m['differential_peak_v']>.05,m['differential_peak_v'],'> 50 mV; CMOS conversion not included')
        if case.startswith('tb_cml_cmos_'):
            for signal in ['cout','cb']:
                edges=crosses(t,d[signal]);edges=edges[edges>cut]
                freq=(len(edges)-1)/(edges[-1]-edges[0]) if len(edges)>2 else 0.
                m[signal+'_frequency_hz']=float(freq)
                m[signal+'_swing_v']=[float(min(d[signal][tail])),float(max(d[signal][tail]))]
                check(signal+' CMOS frequency',abs(freq/target-1)<1e-5,float(freq),f'{target} Hz +/- 10 ppm')
                check(signal+' CMOS swing',m[signal+'_swing_v'][0]<.2 and m[signal+'_swing_v'][1]>1.0,m[signal+'_swing_v'],'low < .2 V, high > 1.0 V')
    elif case.startswith(('tb_lccore_','tb_bank','tb_fine','tb_vco_candidate','tb_vco_loaded_')):
        x=d['vp']-d['vn'];tail=t>150e-9;r=crosses(t,x,level=0);r=r[r>150e-9]
        f=(len(r)-1)/(r[-1]-r[0]) if len(r)>2 else 0.
        m.update(frequency_hz=float(f),differential_peak_v=float(np.ptp(x[tail])/2),max_node_voltage_v=float(max(np.max(d['vp'][tail]),np.max(d['vn'][tail]))))
        m['supply_average_mw']=-1200*average(t,d['VDD:p'],150e-9,200e-9)
        m['power_window_s']=[150e-9,200e-9]
        check('sustained oscillation',m['differential_peak_v']>.05 and f>2e9,[f,m['differential_peak_v']],'> 2 GHz and > .05 V differential peak; feasibility only')
        if case.startswith('tb_vco_loaded_'):
            m['sampler_input_swing_v']=[float(min(d['sp'][tail])),float(max(d['sp'][tail]))]
            m['midpoint_v']=float(np.mean(d['vmid'][tail]))
            diff=d['qp']-d['qn'];edges=crosses(t,diff,level=0);edges=edges[edges>150e-9]
            df=(len(edges)-1)/(edges[-1]-edges[0]) if len(edges)>2 else 0.
            m['cml_frequency_hz']=float(df);m['cml_diff_peak_v']=float(np.ptp(diff[tail])/2)
            check('loaded CML divide two',df>0 and abs(2*df/f-1)<.001,float(df),'within 0.1% of measured free-running VCO/2')
    elif case=='tb_sampler_cp_fine':
        phase=np.deg2rad(np.arange(144,157,3));period=1/24e6
        charge=np.array([-average(t,d[f'VO{i}:p'],90e-9,90e-9+period)*period for i in range(5)])
        y=np.array([np.interp(135e-9,t,d[f'hp{i}']-d[f'hn{i}']) for i in range(5)])
        coeff=np.polyfit(phase,charge,1);ss=np.polyfit(phase,y,1)
        m.update(phase_degrees=np.rad2deg(phase).tolist(),charge_per_cycle_c=charge.tolist(),held_differential_v=y.tolist(),
                 local_kpd_a_rad=float(abs(coeff[0])/period),zero_charge_phase_deg=float(-coeff[1]/coeff[0]*180/np.pi),
                 local_loaded_sampler_v_rad=float(abs(ss[0])),fit_residual_c=float(max(abs(charge-np.polyval(coeff,phase)))),
                 charge_window_s=[90e-9,90e-9+period],sample_time_s=135e-9)
    elif case=='tb_sampler_cp_phase':
        phase=np.arange(12)*2*np.pi/12;period=1/24e6
        charge=np.array([-average(t,d[f'VO{i}:p'],90e-9,90e-9+period)*period for i in range(12)])
        y=np.array([np.interp(135e-9,t,d[f'hp{i}']-d[f'hn{i}']) for i in range(12)])
        X=np.array([np.sin(phase),np.cos(phase),np.ones(12)]).T
        c=np.linalg.lstsq(X,charge,rcond=None)[0];s=np.linalg.lstsq(X,y,rcond=None)[0]
        m.update(phase_sweep_rad=phase.tolist(),charge_per_cycle_c=charge.tolist(),held_differential_v=y.tolist(),
                 kpd_fundamental_a_rad=float(np.hypot(*c[:2])/period),average_offset_current_a=float(c[2]/period),
                 charge_fit_residual_c=float(max(abs(charge-X@c))),loaded_sampler_fundamental_v_rad=float(np.hypot(*s[:2])),
                 held_common_mode_v=[float(np.interp(135e-9,t,(d[f'hp{i}']+d[f'hn{i}'])/2)) for i in range(12)])
    elif case=='tb_sampler_phase':
        y=np.array([d[f'hp{i}'][-1]-d[f'hn{i}'][-1] for i in range(12)]);phase=np.arange(12)*2*np.pi/12
        X=np.array([np.sin(phase),np.cos(phase),np.ones(12)]).T;c=np.linalg.lstsq(X,y,rcond=None)[0]
        m.update(phase_sweep_rad=phase.tolist(),held_differential_v=y.tolist(),fundamental_slope_v_rad=float(np.hypot(*c[:2])),offset_v=float(c[2]),fit_residual_v=float(max(abs(y-X@c))))
        cm=[float((d[f'hp{i}'][-1]+d[f'hn{i}'][-1])/2) for i in range(12)]
        m['held_common_mode_v']=cm
    elif case=='tb_sampler_tt_27':
        m['held_differential_v_at_50ns']=float(np.interp(50e-9,t,d['hp']-d['hn']))
        m['hold_droop_v_45_to_60ns']=float(np.interp(60e-9,t,d['hp']-d['hn'])-np.interp(45e-9,t,d['hp']-d['hn']))
    elif case=='tb_filter_tt_27':
        m['precharged_ctrl_v']=float(np.interp(.99e-6,t,d['ctrl']))
        check('physical precharge',abs(m['precharged_ctrl_v']-.6)<1e-4,m['precharged_ctrl_v'],'0.6 V +/- 0.1 mV')
        # Matched pulse charge changes the total C voltage by about 3.27 mV;
        # transistor turnoff injects extra charge, reported rather than hidden.
        m['final_ctrl_v']=float(d['ctrl'][-1]);m['ctrl_after_open_v']=float(np.interp(1.1e-6,t,d['ctrl']))
    elif case=='tb_cp_compliance':
        rows=[]
        for v in [.2,.3,.4,.6,.8,1.0]:
            ts=10e-9+(v-.2)*100e-9;curr=[float(-np.interp(ts,t,d[f'VO{i}:p'])) for i in range(5)]
            rows.append({'output_v':v,'sink_currents_a':curr,'gm_s':(curr[3]-curr[1])/.02})
        m['compliance_sweep']=rows
    elif case.startswith('tb_cp_pulsed'):
        charge=[-average(t,d[f'VO{i}:p'],40e-9,81.6666666666667e-9)*41.6666666666667e-9 for i in range(5)]
        gain=(charge[3]-charge[1])/.02
        m.update(differential_input_v=[-.05,-.01,0.,.01,.05],charge_c=charge,effective_gm_s=gain/2.083333333333e-9,equivalent_zero_charge_input_v=-charge[2]/gain)
    elif case=='tb_balance_sweep':
        m['duty_sweep']={k:clock_stats(t,d[k],5e-9) for k in d if k.startswith(('rt','out'))}
    else:raise ValueError('Missing measurement for '+case)
    out['outcome']=('characterization' if len(out['checks'])==6 else 'checks_passed') if all(c['passed'] for c in out['checks']) else 'design_check_failed'
    out['waveform_sha256']=hashlib.sha256((work/'waveforms.npz').read_bytes()).hexdigest()
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=[measure(x) for x in sorted((ROOT/'research/runs/spectre_transistor').glob('*/*/result.json'))]
    report={'scope':'Device and mixed-level deterministic simulation; retained negative and incomplete runs are not passing designs.',
            'case_count':len(rows),'counts':{o:sum(r['outcome']==o for r in rows) for o in ['checks_passed','characterization','design_check_failed','execution_incomplete']},'results':rows}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(report['counts'])
if __name__=='__main__':main()
