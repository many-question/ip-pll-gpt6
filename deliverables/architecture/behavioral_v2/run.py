"""Regression for finite-counter acquisition; creates a new, immutable run."""
import argparse
import csv
import hashlib
import json
import os
import shutil
from pathlib import Path
import numpy as np
from acquisition import CFG, FS, bank_hz, run_case, points

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    inputs=args.out/'inputs';inputs.mkdir()
    for p in [Path(__file__),Path(__file__).with_name('acquisition.py'),Path(__file__).parents[1]/'behavioral_v1/model.py',Path(__file__).parents[1]/'behavioral_v1/results/candidate/candidate_B.json']:
        shutil.copy2(p,inputs/p.name)
    os.environ['MPLCONFIGDIR'] = str(args.out / 'matplotlib_cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows, traces = [], {}
    for p in points(CFG):
        for code in [0,127,255]:
            for phase in [0.,.7,2.8,np.pi-.001]:
                row, trace = run_case(p['k'], code, phase, samples=960)
                rows.append(row)
                if code == 127 and phase == .7 and p['k'] in [9,14,41]:
                    traces[p['k']] = trace
    with (args.out/'acquisition.csv').open('w', newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    stress=[]
    for p in points(CFG):
        for scale in [.99,1.01]:
            row,_=run_case(p['k'],bank_scale=scale,samples=1200)
            stress.append(row)
    with (args.out/'bank_sensitivity.csv').open('w', newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=stress[0].keys(),lineterminator='\n')
        writer.writeheader(); writer.writerows(stress)
    # Real endpoint coverage limit: +3% bank shift cannot reach low endpoint.
    negative,_=run_case(28,bank_scale=1.03,samples=1200)
    recovery,rt=run_case(41,disturbance_hz=-24e6,disturbance_cycle=800,samples=2000)
    fine,tr=run_case(41,substeps=16,samples=960)
    coarse=next(r for r in rows if r['k']==41 and r['initial_code']==127 and r['phase0_rad']==.7)
    checks=[
        {'name':'33 frequencies x 3 initial codes x 4 phases capture correct harmonic',
         'passed':all(r['settled'] for r in rows),'cases':len(rows),'failed':[r for r in rows if not r['settled']]},
        {'name':'bank frequency scale +/-1 percent functional sensitivity','passed':all(r['settled'] for r in stress),
         'cases':len(stress),'failed':[r for r in stress if not r['settled']]},
        {'name':'24 MHz disturbance triggers reacquisition','passed':recovery['settled'] and recovery['searches']>1,'result':recovery},
        {'name':'out-of-range bank cannot be falsely accepted','passed':not negative['settled'],'result':negative},
        {'name':'intracycle 16 substeps agree with exact reference-period solution','passed':abs(fine['final_error_hz']-coarse['final_error_hz'])<.01 and fine['rail_violation_cycles']==0},
    ]
    result={'model':'sspll-acquisition/2.0','checks':checks,'all_passed':all(c['passed'] for c in checks),
            'nominal_passed':sum(r['settled'] for r in rows),'nominal_cases':len(rows),
            'worst_settling_us':max(r['settling_us'] or 0 for r in rows),
            'control_range_v':[min(r['control_min_v'] for r in rows),max(r['control_max_v'] for r in rows)],
            'largest_bank_step_hz':float(max(-np.diff(bank_hz(np.arange(256))))),
            'counter_window_refcycles':32,'counter_resolution_hz':FS/32,
            'bank_nominal_limits_hz':[float(bank_hz(255)),float(bank_hz(0))],
            'limits':['Nominal equal-C bank and fixed Kvco are hypotheses, no PVT model.',
                      'Rail crossing flags invalidate a case; no claim to simulate nonlinear clamp recovery.',
                      'FLL precharge idealizes a finite low-resistance reset; oscillator phase is not reset.',
                      'Behavioral V2 adds deterministic acquisition; V1 noise assumptions and limitations remain.']}
    (args.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True)
    for k,tr in traces.items():
        np.savetxt(args.out/f'trace_k{k}.csv',tr,delimiter=',',header='time_s,code,state,phase_error_rad,vctrl_v,vc1_v,fvco_hz,searches',comments='')
        axs[0].plot(tr[:,0]*1e6,tr[:,1],label=f'K={k}')
        axs[1].plot(tr[:,0]*1e6,tr[:,4]); axs[2].plot(tr[:,0]*1e6,tr[:,3])
    axs[0].set_ylabel('Bank code');axs[0].legend()
    axs[1].set_ylabel('Vctrl (V)');axs[2].set_ylabel('Phase error (rad)');axs[2].set_xlabel('Time (us)')
    for ax in axs: ax.grid(alpha=.25)
    fig.tight_layout();fig.savefig(args.out/'acquisition.png',dpi=140);plt.close(fig)
    np.savetxt(args.out/'recovery.csv',rt,delimiter=',',header='time_s,code,state,phase_error_rad,vctrl_v,vc1_v,fvco_hz,searches',comments='')
    sources=[Path(__file__),Path(__file__).with_name('acquisition.py')]
    (args.out/'manifest.json').write_text(json.dumps({'inputs_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}},indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))
    return 0 if result['all_passed'] else 1

if __name__=='__main__':raise SystemExit(main())
