"""Summarize tested circuit deltas, preserving failed setups and corner attempts."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H,R


def main():
    rows=json.loads((H/'results/validation.json').read_text())
    by={r['case']:r for r in rows}
    noise=json.loads((H/'results/noise_validation.json').read_text())
    nb={r['case']:r for r in noise['cases']}
    prior=H.parent/'cmos_v12'
    oldnoise=json.loads((prior/'results/noise_validation.json').read_text())
    old=next(r for r in oldnoise['cases'] if r['case']=='noise_one32_fine')
    new=nb['noise_cc4_rtcomb_fine']
    coarse=nb['noise_cc4_rtcomb_coarse']
    table=[]
    for r in rows:
        w=r.get('wave',{});n=nb.get(r['case'],{})
        table.append(dict(case=r['case'],run=r['run'],simulator_ok=r['sim_ok'],
            boundary='actual_LC_fixed_control' if r['case'].startswith('lc_') else 'ideal_source_fixture',
            function_pass=w.get('pass_function',False),RF_hz=w.get('reference_RF_frequency_hz'),
            output_hz=w.get('signals',{}).get('out',{}).get('frequency_hz'),
            power_mw=w.get('power_mw',{}).get('VDD:p'),
            noise_valid=n.get('valid_noise'),noise_options_ignored=n.get('noise_option_ignored'),
            jitter_fs=n.get('numeric_jitter_fs')))
    with (H/'results/cases.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    base='lc_cc4rt_c21_v0p2_i100_tt';hi='lc_cc4rt_c21_v1p0_i100_tt'
    a=by[base]['wave'];b=by[base+'_fine']['wave'];c=by[hi]['wave']
    df=b['reference_RF_frequency_hz']/a['reference_RF_frequency_hz']-1
    dp=b['power_mw']['VDD:p']/a['power_mw']['VDD:p']-1
    lcprec=dict(coarse_case=base,fine_case=base+'_fine',relative_RF_change=df,relative_power_change=dp,
        pass_precision=bool(a['pass_function'] and b['pass_function'] and abs(df)<.001 and abs(dp)<.01))
    lcbracket=dict(low_case=base,high_case=hi,RF_hz=[a['reference_RF_frequency_hz'],c['reference_RF_frequency_hz']],
        pass_endpoint_bracket=bool(a['pass_function'] and c['pass_function'] and a['reference_RF_frequency_hz']<3936e6<c['reference_RF_frequency_hz']),
        scope='Fixed control, not lock; endpoints do not prove monotonic coverage.')
    changes=[]
    for key,label in [('noise_cc4_base_coarse','Only coupling capacitor1->4pF'),('noise_cc4_rtout_coarse','4pF + MP2x1.5,first bufferNMOSx2'),('noise_cc4_rtpre_coarse','4pF + MN1/MNC1x1.5'),('noise_cc4_rtcomb_coarse','4pF + both local changes')]:
        r=nb[key];changes.append(dict(case=key,change=label,jitter_fs=r['numeric_jitter_fs'],power_mw=r['periodic']['power_mw']['VDD:p'],valid_noise=r['valid_noise']))
    summary=dict(counts=dict(recovered=len(rows),simulator_ok=sum(r['sim_ok'] for r in rows),
            function_pass=sum(r.get('wave',{}).get('pass_function',False) for r in rows),
            noise_cases=len(noise['cases']),valid_noise=sum(r['valid_noise'] for r in noise['cases']),
            rejected_noise_option_setups=sum(r.get('noise_option_ignored',False) for r in noise['cases'])),
        preferred_TT_candidate=dict(receiver='rf_cc4_v13',divider='cmos_tspc_buffered_v11',retimer='rtcomb_v13',
            old_fine_jitter_fs=old['numeric_jitter_fs'],new_fine_jitter_fs=new['numeric_jitter_fs'],
            relative_jitter_change=new['numeric_jitter_fs']/old['numeric_jitter_fs']-1,
            old_forced_power_mw=old['periodic']['power_mw']['VDD:p'],new_forced_power_mw=new['periodic']['power_mw']['VDD:p'],
            noise_scope='TT27,1.2V,ideal noiseless RF20-harmonic waveform,3.936GHz,984MHz output,10fF,10kHz-492MHz,rising0.6V. No actualLCsourceimpedance/noise/feedback.'),
        controlled_changes=changes,noise_precision=noise['precision']['noise_cc4_rtcomb'],
        gating=json.loads((H/'results/gating_validation.json').read_text()),
        actual_LC_precision=lcprec,actual_LC_bracket=lcbracket,
        actual_LC_cases=[dict(case=r['case'],run=r['run'],wave=r.get('wave')) for r in rows if r['case'].startswith('lc_')],
        final_corner_screens={corner:by['screen_cc4rt_'+corner]['wave'] for corner in ['ss','ff']},
        clock_input_window=[dict(case=r['case'],wave=r.get('wave')) for r in rows if r['case'].startswith('screen_clock_')],
        remaining=['SS60 receiver plus divider pulse/timing robustness','Full actualLC+PLLnoise and backaction','Six CMOS division modes and reset/hold timing','Full power/bias/FLL,33channels,PVT/MC/PEX/area'])
    (H/'results/summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    # All implementation comparison bars use coarse settings; the two headline
    # endpoints also have independent finer runs and remain separately recorded.
    ob=next(r for r in oldnoise['cases'] if r['case']=='noise_one32_coarse')
    fig,axs=plt.subplots(1,2,figsize=(11.8,4.2),layout='constrained')
    vals=[ob['numeric_jitter_fs']]+[x['jitter_fs'] for x in changes]
    axs[0].bar(range(5),vals,color=['#8a9297','#6d99a3','#5489a8','#377691','#167d68'])
    axs[0].set_xticks(range(5),['v12','4 pF','Output\nbranch','Evaluation\nbranch','Combined'])
    for i,v in enumerate(vals):axs[0].text(i,v+3,f'{v:.1f}',ha='center',fontsize=9)
    axs[0].set(ylim=(0,210),ylabel='RMS output jitter (fs)',title='Controlled local changes, coarse grid\nTT27, ideal low-swing RF,10 kHz–492 MHz')
    keys=['XRX','XD','XR'];idx=np.arange(3)
    ov=[ob['noise_by_instance'][k]['jitter_fs'] for k in keys]
    nv=[coarse['noise_by_instance'][k]['jitter_fs'] for k in keys]
    axs[1].bar(idx-.18,ov,.36,label='v12',color='#8a9297');axs[1].bar(idx+.18,nv,.36,label='v13 combined',color='#167d68')
    for i,v in enumerate(nv):axs[1].text(i+.18,v+3,f'{v:.1f}',ha='center',fontsize=9)
    axs[1].set_xticks(idx,['Receiver','Divider','Retimer + buffer'])
    axs[1].set(ylim=(0,195),ylabel='Output-referred contribution (fs)',title='Independent noise-on verified\nContributions combine by variance')
    axs[1].legend();fig.savefig(H/'results/noise_optimization.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(counts=summary['counts'],preferred=summary['preferred_TT_candidate'],LC_precision=lcprec,LC_bracket=lcbracket),indent=2))


if __name__=='__main__':main()
