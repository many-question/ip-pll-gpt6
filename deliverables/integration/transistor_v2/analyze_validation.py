"""Postprocess completed circuit runs; no inferred pass from Spectre exit alone."""
from pathlib import Path
import json,re
import numpy as np

H=Path(__file__).resolve().parent
D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_transistor_v2'
def edge(t,v,level=.6):
    i=np.flatnonzero((v[:-1]<level)&(v[1:]>=level))
    return t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])
def average(t,v):return float(np.trapezoid(v,t)/(t[-1]-t[0]))
def word(z,prefix,n):return sum((z[f'{prefix}{i}']>.6).astype(int)*(1<<i) for i in range(n))
def load(run,case):
    p=R/run/case
    if not (p/'result.json').exists():return None
    result=json.loads((p/'result.json').read_text())
    if not result['ok']:return None
    if not result.get('remote_inputs_match'):return None
    assert '0 errors' in (p/'spectre.out').read_text(errors='replace')[-6500:]
    return np.load(p/'waveforms.npz'),(p/'inputs'/(case+'.scs')).read_text()
def main():
    out={'divider':[],'divider_light':[],'loaded_chain':[],'fll_counter':[],'fll_window':[],'fll_controller':[],'fll_controller_r3':[],'fll_coupled_prefix':[],'mixed_loop':[]}
    for corner,light in [(c,l) for l in [False,True] for c in ['ss','tt','ff']]:
        for m in [4,6,8,10,12,14]:
            run='divider10' if corner=='ss' and m in [4,6] else 'divider11'
            case=f'tb_bank_m{m}_{corner}';data=load(run,case)
            if light:
                run='divider12' if corner=='ss' and m in [4,6] else 'divider13'
                case+='_light';data=load(run,case)
            if data is None:continue
            z,net=data;t=z['time'];mask=t>=60e-9;t=t[mask];v=z['out'][mask]
            fin=float(re.search(r'freq=([\d.]+)',net)[1]);expected=fin/m
            e=edge(t,v);period=np.diff(e);relative=period*expected-1
            good=bool(len(e)>2 and abs(len(e)-expected*(t[-1]-t[0]))<=1.1 and np.max(abs(relative))<.02 and v.min()<.2 and v.max()>1.0)
            out['divider_light' if light else 'divider'].append(dict(run=run,case=case,corner=corner,m=m,input_hz=fin,expected_hz=expected,
                mean_output_hz=1/float(period.mean()),edge_count=len(e),max_period_relative_error=float(np.max(abs(relative))),
                output_min_v=float(v.min()),output_max_v=float(v.max()),power_mw=-1.2*average(t,z['VDD:p'][mask])*1e3,
                start_s=float(t[0]),end_s=float(t[-1]),passed=good))
    for run,light in [('loaded04',False),('divider13',True)]:
      for case in ['tb_loaded_final_c0_lo','tb_loaded_final_c0_hi','tb_loaded_final_c255_lo','tb_loaded_final_c255_hi']:
        if light:case+='_light60'
        data=load(run,case)
        if data is None:continue
        z,net=data;t=z['time'];mask=t>=100e-9;t=t[mask];ev=edge(t,(z['vp']-z['vn'])[mask],0);eo=edge(t,z['out'][mask])
        fv=1/np.mean(np.diff(ev));fo=1/np.mean(np.diff(eo));m=8 if 'c255' in case else 4
        current={k:dict(mean_a=average(t,z[k][mask]),peak_abs_a=float(np.max(abs(z[k][mask])))) for k in z.files if '.MP:b' in k}
        out['loaded_chain'].append(dict(run=run,case=case,corner='tt',temperature_c=27,fixed_cap_f=(60 if light else 40)*1e-15,m=m,
            vco_hz=float(fv),output_hz=float(fo),ratio_error_ppm=float((fv/fo/m-1)*1e6),
            output_min_v=float(z['out'][mask].min()),output_max_v=float(z['out'][mask].max()),
            divider_input_min_v=float(min(z['XD.icp'][mask].min(),z['XD.icn'][mask].min())),
            divider_input_max_v=float(max(z['XD.icp'][mask].max(),z['XD.icn'][mask].max())),
            power_mw=-1.2*average(t,z['VDD:p'][mask])*1e3,clock_gate_bulk_current=current,
            passed=bool(abs(fv/fo/m-1)<.002)))
    for run,corner in [(r,c) for r in ['fll01','fll12'] for c in ['tt','ss','ff']]:
        case='tb_fll_counter_'+corner;data=load(run,case)
        if data is None:continue
        z,net=data;count=int(word(z,'q',14)[-1])
        out['fll_counter'].append(dict(run=run,case=case,clock_hz=1e9,gate_s=256e-9,expected_count=256,actual_count=count,passed=count==256))
    for corner in ['tt','ss','ff']:
        case='tb_fll_counter_1200_'+corner;data=load('fll17',case)
        if data is None:continue
        z,net=data;count=int(word(z,'q',14)[-1])
        out['fll_counter'].append(dict(run='fll17',case=case,clock_hz=1.2e9,gate_s=256e-9,
            expected_count=307,actual_count=count,passed=count==307,
            condition='Startup headroom check; 307 complete input edges for the specified clock/gate phase, not an integer-cycle window'))
    for run in ['fll11','fll12']:
        data=load(run,'tb_fll_counter_window')
        if data is None:continue
        z,net=data;count=int(word(z,'q',14)[-1]);snap=int(word(z,'m',14)[-1])
        hold=(z['time']>50e-9)&(z['time']<10.7e-6)
        held=bool(np.all(word(z,'m',14)[hold]==0))
        out['fll_window'].append(dict(run=run,clock_hz=984e6,gate_s=256/24e6,expected_count=10496,
             actual_count=count,snapshot=snap,bus_held_during_measurement=held,passed=count==10496 and snap==count and held))
    for run,case in [('fll10','tb_fll_controller_functional'),('fll09','tb_fll_controller_tt')]:
        data=load(run,case)
        if data is None:continue
        z,net=data;t=z['time'];coarse=word(z,'coarse',8);dac=word(z,'dac',6)
        starts=np.flatnonzero((z['count_gate'][:-1]<.6)&(z['count_gate'][1:]>=.6))+1
        stops=np.flatnonzero((z['count_gate'][:-1]>=.6)&(z['count_gate'][1:]<.6))+1
        gates=[dict(start_s=float(t[a]),duration_s=float(t[b]-t[a]),coarse=int(coarse[a]),dac=int(dac[a])) for a,b in zip(starts,stops)]
        en=np.flatnonzero(z['enable']>.6);et=float(t[en[0]]) if len(en) else None
        good=bool(len(gates)==14 and np.max(abs(np.array([g['duration_s'] for g in gates])-256/24e6))<=21e-9 and et and z['range_error'][-1]<.6 and coarse[-1]==12 and dac[-1]==23)
        out['fll_controller'].append(dict(run=run,case=case,measurement='analytic finite-count macro; MOS controller/snapshot/DAC/filter',
            reltol=float(re.search(r'reltol=([\de.-]+)',net)[1]),gates=gates,enable_s=et,
            final_coarse=int(coarse[-1]),final_dac=int(dac[-1]),final_ctrl_v=float(z['ctrl'][-1]),
            final_output_hz=float(z['freq_ghz'][-1]*1e9),locked_controller_dac_power_mw=float(z['pmw'][-1]),passed=good))
    if len(out['fll_controller'])==2:
        a,b=out['fll_controller'];out['fll_numerical_comparison']=dict(
            final_control_difference_v=abs(a['final_ctrl_v']-b['final_ctrl_v']),
            identical_codes_and_handoff=all(a[k]==b[k] for k in ['final_coarse','final_dac','enable_s']),
            condition='reltol 1e-2 vs 1e-3, functional acquisition only; not noise accuracy')
    for run,case,expected_windows,expected_code,expect_error in [
          ('fll14','tb_fll_controller_r3',15,12,False),
          ('fll15','tb_fll_controller_r3_zero',7,0,False),
          ('fll15','tb_fll_controller_r3_rangehigh',7,0,True)]:
        data=load(run,case)
        if data is None:continue
        z,net=data;t=z['time'];coarse=word(z,'coarse',8);dac=word(z,'dac',6);state=word(z,'state_out',3)
        starts=np.flatnonzero((z['count_gate'][:-1]<.6)&(z['count_gate'][1:]>=.6))+1
        stops=np.flatnonzero((z['count_gate'][:-1]>=.6)&(z['count_gate'][1:]<.6))+1
        gates=[dict(start_s=float(t[a]),duration_s=float(t[b]-t[a]),coarse=int(coarse[a]),dac=int(dac[a])) for a,b in zip(starts,stops)]
        en=np.flatnonzero(z['enable']>.6);done=np.flatnonzero(state==5)
        range_error=bool(z['range_error'][-1]>.6);enabled=bool(z['enable'][-1]>.6)
        freq=float(z['freq_ghz'][-1]*1e9)
        good=bool(len(gates)==expected_windows and np.max(abs(np.array([g['duration_s'] for g in gates])-256/24e6))<=21e-9
            and len(done) and int(coarse[-1])==expected_code and range_error==expect_error and enabled!=expect_error
            and (expect_error or abs(freq-984e6)<=187500))
        out['fll_controller_r3'].append(dict(run=run,case=case,measurement='MOS controller/snapshot/DAC/filter with analytic finite-count macro',
            gates=gates,enable_s=float(t[en[0]]) if len(en) else None,done_s=float(t[done[0]]) if len(done) else None,
            final_coarse=int(coarse[-1]),final_dac=int(dac[-1]),final_ctrl_v=float(z['ctrl'][-1]),
            final_output_hz=freq,range_error=range_error,enabled=enabled,post_completion_branch_power_mw=float(z['pmw'][-1]),
            passed=good,reltol=1e-2,condition='TT/27 C, 1.2 V; rangehigh intentionally unreachable'))
    for run,case,expected_count,final_code in [('fll13','tb_fll_acquire_first_window',8939,64),('fll16','tb_fll_acquire_r3_first_window',10645,128)]:
        data=load(run,case)
        if data is None:continue
        z,net=data;t=z['time'];coarse=np.rint(z['code_mon']).astype(int)
        stable=((np.rint(z['state_mon'])==2)|(np.rint(z['state_mon'])==3))&(z['count_gate']<.6)&(z['count_mon']>1)
        counted=np.rint(z['count_mon'][stable]).astype(int)
        count_ok=bool(len(counted) and np.all(abs(counted-expected_count)<=1))
        out['fll_coupled_prefix'].append(dict(run=run,stop_s=float(t[-1]),final_coarse=int(coarse[-1]),
             final_enable_v=float(z['enable'][-1]),measurement='MOS counter/controller/snapshot/DAC/filter, analytic VCO plant',
             nonzero_observed_counts=np.unique(np.rint(z['count_mon'][z['count_mon']>1]).astype(int)).tolist(),
             expected_first_count_rounded=expected_count,stable_drain_counts=np.unique(counted).tolist(),
             passed=bool(coarse[-1]==final_code and z['enable'][-1]<.6 and count_ok),
             scope='First complete measurement and SAR update only, not full acquisition'))
    for run,case in [('system08','loop_s8_divider'),('system09','loop_s9_noise_output')]:
        data=load(run,case)
        if data is None:continue
        z,net=data;t=z['time'];sel=t>=5.5e-6
        out['mixed_loop'].append(dict(run=run,case=case,final={k:float(z[k][-1]) for k in z.files if k!='time'},
            final_output_hz=float(z['freqout'][-1]*1e9),monitor_units={'freqout':'GHz','dutyout':'fraction','power_mw':'mW'},
            cycle_ctrl_pp_v=float(np.ptp(z['cycle_ctrl'][sel])),raw_ctrl_pp_v=float(np.ptp(z['ctrl'][sel])),
            passed=bool(abs(z['freqout'][-1]-.984)/.984<1e-6 and np.ptp(z['cycle_ctrl'][sel])<1e-4)))
    out['coverage_note']='Endpoint frequencies, paired TT/27 C SS/60 C FF/0 C, 1.2 V. Not full PVT or all-channel signoff. Loaded chain open loop. FLL counter and controller validated separately.'
    (H/'results/validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
