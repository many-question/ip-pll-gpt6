"""Collect circuit evidence without transferring claims across source boundaries."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H, R


def main():
    rows = json.loads((H/'results/validation.json').read_text())
    noise = json.loads((H/'results/noise_validation.json').read_text())
    by = {r['case']: r for r in rows}
    nb = {r['case']: r for r in noise['cases']}
    table = []
    for r in rows:
        w = r.get('wave', {})
        n = nb.get(r['case'], {})
        table.append(dict(case=r['case'], run=r['run'], simulator_ok=r['sim_ok'],
            boundary='actual_LC_fixed_control' if r['case'].startswith('lc_') else 'ideal_voltage_RF_replay',
            function_pass=w.get('pass_function', False),
            RF_hz=w.get('reference_RF_frequency_hz'),
            output_hz=w.get('signals', {}).get('out', {}).get('frequency_hz'),
            fixture_power_mw=w.get('power_mw', {}).get('VDD:p'),
            noise_valid=n.get('valid_noise'), jitter_fs=n.get('numeric_jitter_fs')))
    with (H/'results/cases.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]))
        writer.writeheader(); writer.writerows(table)
    lc = []
    for r in rows:
        if not r['case'].startswith('lc_') or 'wave' not in r:
            continue
        w = r['wave']
        with np.load(R/r['run']/r['case']/'waveforms.npz') as z:
            duration = float(z['time'][-1]-z['time'][0])
        lc.append(dict(case=r['case'], pass_function=w['pass_function'],
            RF_hz=w['reference_RF_frequency_hz'], output_hz=w['signals']['out']['frequency_hz'],
            clock_range_v=w['signals']['clk']['range_v'], RF_diff_range_v=w['signals']['rf']['range_v'],
            power_mw=w['power_mw'], observation_s=duration,
            reference_cycles_observed=duration*24e6,
            covers_reference_cycle=duration*24e6>=1))
    base='lc_one32_c21_v0p2_tt_i100'
    high='lc_one32_c21_v1p0_tt_i100'
    low=by[base]['wave']; hi=by[high]['wave']; fine=by[base+'_fine']['wave']
    protocol=json.loads((H/'results/protocol_final_tuning.json').read_text())
    df=fine['reference_RF_frequency_hz']/low['reference_RF_frequency_hz']-1
    dp=fine['power_mw']['VDD:p']/low['power_mw']['VDD:p']-1
    precision=dict(coarse_case=base, fine_case=base+'_fine',
        relative_RF_change=df, relative_power_change=dp,
        pass_precision=bool(low['pass_function'] and fine['pass_function'] and
            abs(df)<protocol['limits']['lc_refine_frequency_relative'] and
            abs(dp)<protocol['limits']['lc_refine_power_relative']))
    bracket=dict(target_RF_hz=3936e6, low_case=base, high_case=high,
        RF_endpoints_hz=[low['reference_RF_frequency_hz'],hi['reference_RF_frequency_hz']],
        pass_endpoint_bracket=bool(low['pass_function'] and hi['pass_function'] and
            low['reference_RF_frequency_hz']<3936e6<hi['reference_RF_frequency_hz']),
        note='Endpoint bracket only. No proof of monotonic coverage or PLL lock.')
    summary=dict(boundaries=dict(noise='Ideal noiseless low-swing voltage waveform source; no LC source impedance/noise or feedback.',
        actual_LC='Physical Q5 RLC and PDK MOS, real sampler/CP/reference-buffer and CMOS chain. Fixed code/control, bias generators and FLL omitted. Not PLL lock or full power signoff.'),
        counts=dict(recovered=len(rows), simulator_ok=sum(r['sim_ok'] for r in rows),
            function_pass=sum(r.get('wave',{}).get('pass_function',False) for r in rows),
            valid_noise=sum(r['valid_noise'] for r in noise['cases']),
            noise_precision_pass=sum(r['pass_precision'] for r in noise['precision'].values())),
        preferred_forced_case='noise_one32_fine',
        forced_jitter_fs=nb['noise_one32_fine']['numeric_jitter_fs'],
        forced_fixture_power_mw=nb['noise_one32_fine']['periodic']['power_mw']['VDD:p'],
        gating=json.loads((H/'results/gating_validation.json').read_text()),
        actual_LC_cases=lc, actual_LC_precision=precision, actual_LC_bracket=bracket,
        corner_screen={c:by['screen_one32_'+c]['wave'] for c in ['ss','ff']},
        exclusions={'noise_one32_rt3_coarse':'PSS returned an unusable orbit; no crossing event, no valid pnoise measurement.',
                    'noise_one32_rt4_coarse':'PSS did not converge; pnoise skipped. Large SOA warnings belong to failed shooting iterations, not accepted operating points.'},
        unrun_testbenches=sorted(p.stem for p in (H/'tb').glob('*.scs') if p.stem not in by),
        remaining=['SS60 high-frequency receiver margin', 'Actual LC plus digital device noise including feedback',
                   'Retimer noise and clock-capacitance tradeoff', 'Six divider modes, reset/hold and timing validation',
                   'Closed PLL/FLL and all33frequency/PVT points', 'Bias/reference generators, full power, area, PEX/reliability'])
    (H/'results/summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    fig, axs=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    groups=summary['gating']['cases']
    axs[0].bar(['RF receiver','Divider','Retimer + buffer'],[x['jitter_fs'] for x in groups],color=['#177e89','#498b47','#db8b24'])
    for i,g in enumerate(groups): axs[0].text(i,g['jitter_fs']+4,f"{g['jitter_fs']:.1f} fs",ha='center')
    axs[0].set(ylim=(0,205),ylabel='Output-referred RMS jitter (fs)',title='Independent noise-on, TT27\nIdeal low-swing RF source, 10 kHz–492 MHz')
    variants=['lc_one32_c17_v0p6_tt','lc_one32_c17_v0p6_tt_i100','lc_one32_c17_v0p6_tt_i120']
    for name,col,label in zip(variants,['#be4040','#177e89','#6b5fa7'],['80 uA: FAIL','100 uA: PASS','120 uA: PASS']):
        r=by[name]
        with np.load(R/r['run']/name/'waveforms.npz') as z:
            t=z['time']; v=z['clk']; end=t[-1]; ix=(t>end-1.5e-9)
            # Independent autonomous phase is preserved; comparisons are of swing.
            axs[1].plot((t[ix]-end)*1e9,v[ix],label=label,color=col,lw=1.2)
    axs[1].axhline(1,color='gray',ls=':',lw=.8);axs[1].axhline(.2,color='gray',ls=':',lw=.8)
    axs[1].set(xlabel='Time relative to 400 ns (ns)',ylabel='Receiver clock (V)',title='Actual LC, code17/control0.6V, TT27\nFixed control; not a locked PLL')
    axs[1].legend(fontsize=8,loc='lower left')
    fig.savefig(H/'results/cmos_evidence.png',dpi=150)
    plt.close(fig)
    print(json.dumps(dict(counts=summary['counts'],actual_LC_precision=precision,actual_LC_bracket=bracket),indent=2))


if __name__=='__main__':
    main()
