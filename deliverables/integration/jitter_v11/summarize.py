"""Generate compact tables/figures from validated, locally recovered Spectre results."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H

def main():
 n=json.loads((H/'results/noise_validation.json').read_text());by={r['case']:r for r in n['cases']}
 selected=['noise_cmos_buf_s2_r10_fine','noise_cmos_buf_s4_r10_fine','noise_cmos_rt_s8_fine','noise_cmos_rt_s4_sp25_ck10_fine','noise_cmos_rt_s4_sp25_ck50_fine','noise_cmos_chain_direct_fine','noise_cmos_chain_inv_fine']
 result=[]
 for c in selected:
  r=by[c];precision=n['precision'][c.removesuffix('_fine')];assert r['valid_noise'] and precision['pass_precision']
  result.append(dict(case=c,jitter_fs=r['numeric_jitter_fs'],fixture_power_mw=r['periodic']['power_mw']['VDD:p'],precision=precision,scope='TT27,1.2V,ideal external fullrail clock/input;10fF;10kHz-492MHz. Actual CMOS devices, no real LC interface or source-driver power.'))
 gating=json.loads((H/'results/gating_validation.json').read_text());assert gating['pass_gating']
 val=json.loads((H/'results/validation.json').read_text());ex=[r for r in val if 'excluded_from_design_conclusions' in r]
 f=[r for r in val if r['case'].startswith(('probe_','cmos_')) and r not in ex]
 summary=dict(selected=result,noise_cases=len(n['cases']),valid_noise_cases=sum(bool(r['valid_noise']) for r in n['cases']),precision_pairs_passed=sum(bool(v['pass_precision']) for v in n['precision'].values()),function_trials=dict(valid_protocol_count=len(f),passed=sum(bool(r.get('wave',{}).get('pass_function')) for r in f),excluded_initialization_trials=len(ex)),gating=gating,conclusion='CMOS is the preferred research direction. 100fs-class intrinsic retiming is demonstrated; fullPLL performance remains unqualified. CML continuation was motivated by poor GHz receiver interface, not demonstrated necessity at this frequency.')
 (H/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 table=['| Case | RMS jitter fs | Measured VDD power mW | Precision |','|---|---:|---:|---|']
 for r in n['cases']:
  if not r['valid_noise']:continue
  key=r['case'].removesuffix('_fine').removesuffix('_coarse');prec=n['precision'].get(key,{}).get('pass_precision',False)
  table.append(f"| {r['case']} | {r['numeric_jitter_fs']:.3f} | {r['periodic']['power_mw']['VDD:p']:.6f} | {'coarse+fine passed' if prec else 'coarse only'} |")
 (H/'results/noise_table.md').write_text('TT27,1.2V,984MHz output,10fF,10kHz-492MHz. Ideal source drive; excludes real source-driver energy. Single-on rows are contributions, not total noise.\n\n'+'\n'.join(table)+'\n')
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 fig,ax=plt.subplots(1,3,figsize=(14,4.1),layout='constrained')
 scales=[1,2,4];vals=[by[f'noise_cmos_buf_s{s}_r10_coarse']['numeric_jitter_fs'] for s in scales]
 ax[0].plot(scales,vals,'o-',label='CMOS buffer')
 ax[0].plot(scales,vals[0]/np.sqrt(scales),'--',alpha=.7,label='1/sqrt(size) reference')
 ax[0].set(xlabel='Uniform width scale',ylabel='RMS jitter (fs)',title='Size helps a valid CMOS stage',xticks=scales);ax[0].legend()
 slews=[10,100,300];a=[by[f'noise_cmos_buf_s1_r{s}_coarse']['numeric_jitter_fs'] for s in slews];b=[by[f'noise_restorer_small_r{s}_coarse']['numeric_jitter_fs'] for s in slews]
 ax[1].plot(slews,a,'o-',label='Full swing, CMOS buffer');ax[1].plot(slews,b,'s-',label='0.25 V, AC restorer')
 ax[1].set(xlabel='Input rise/fall time (ps)',ylabel='RMS jitter (fs)',title='Slew controls within each fixture');ax[1].legend(fontsize=8)
 names=['Buffer x2','Retimer + buffer','CMOS chain\ndirect','CMOS chain\ninverted']
 vals=[by[k]['numeric_jitter_fs'] for k in [selected[0],selected[3],selected[5],selected[6]]]
 ax[2].bar(names,vals,color=['#31859b','#31859b','#607bb8','#607bb8']);ax[2].axhline(100,color='gray',ls='--',lw=1)
 for i,v in enumerate(vals):ax[2].text(i,v+3,f'{v:.2f}',ha='center')
 ax[2].set(ylabel='RMS jitter (fs)',title='Refined results, ideal external drive',ylim=(0,160));ax[2].tick_params(axis='x',labelsize=8)
 fig.suptitle('TSMC180 BCD Gen2 | 1.2 V | TT27 | 984 MHz | 10 fF | 10 kHz-492 MHz',fontsize=12)
 p=H/'results/jitter_diagnosis.png';fig.savefig(p,dpi=160);plt.close(fig)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
