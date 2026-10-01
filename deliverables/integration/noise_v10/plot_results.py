"""Show independent gating agreement and one-module optimization evidence."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H

def main():
 out=H/'figures';out.mkdir(exist_ok=True);g=json.loads((H/'results/gating_validation.json').read_text());order=['divider','master','slave','output','bias'];rows=sorted([r for r in g['cases'] if r['group'] in order],key=lambda r:order.index(r['group']))
 if rows:
  x=np.arange(len(rows));fig,ax=plt.subplots(figsize=(9,4.8),constrained_layout=True)
  a=[r['expected_from_all_on_fs'] for r in rows];b=[r['jitter_fs'] for r in rows]
  ax.bar(x-.18,a,.36,label='Device sum from all-on');ax.bar(x+.18,b,.36,label='Independent single-on')
  for i,y in enumerate(b):ax.text(i+.18,y+7,f'{y:.2f}',ha='center',fontsize=9)
  ax.set(xticks=x,xticklabels=[r['group'] for r in rows],ylabel='RMS contribution at output (fs)',title='Noise-source gating: TT27, 984 MHz, 10 kHz–492 MHz')
  ax.legend();ax.grid(axis='y',alpha=.2);fig.savefig(out/'gating_contributions.png',dpi=160);plt.close(fig)
 p=H/'results/optimization_validation.json'
 if not p.exists():return
 d=json.loads(p.read_text());rows=[r for r in d['cases'] if r.get('only',{}).get('valid_noise')]
 if rows:
  x=np.arange(len(rows));fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True,constrained_layout=True)
  a=[r['only']['baseline_jitter_fs'] for r in rows];b=[r['only']['jitter_fs'] for r in rows]
  ax[0].bar(x-.18,a,.36,label='Baseline selected module');ax[0].bar(x+.18,b,.36,label='One-module modification')
  ax[0].set(ylabel='Selected-only RMS (fs)',title='One-module changes at actual chain loading; same TT fixture');ax[0].legend()
  ax[1].bar(x,[r['only']['power_delta_mw'] for r in rows]);ax[1].axhline(0,color='gray');ax[1].set(xticks=x,xticklabels=[r['case'].removeprefix('opt_').removesuffix('_tt') for r in rows],ylabel='Chain power change (mW)')
  for row in ax:row.grid(axis='y',alpha=.2)
  fig.savefig(out/'module_optimization.png',dpi=160);plt.close(fig)
 n=json.loads((H/'results/noise_validation.json').read_text());by={r['case']:r for r in n['cases']};full=[r for r in d['cases'] if r.get('all',{}).get('valid_noise')]
 if full:
  base=by['noise_gate_all_coarse'];labels=['baseline'];jit=[base['numeric_jitter_fs']];power=[base['periodic']['power_mw']['VDD:p']];qualified=[False]
  for r in full:
   key=r['all']['case'].removesuffix('_coarse');fine=by.get(key+'_fine');ok=n['precision'].get(key,{}).get('pass_precision',False)
   q=fine if fine and ok else by[r['all']['case']]
   labels.append(r['case'].removeprefix('opt_').removesuffix('_tt'));jit.append(q['numeric_jitter_fs']);power.append(q['periodic']['power_mw']['VDD:p']);qualified.append(ok)
  x=np.arange(len(labels));fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True,constrained_layout=True)
  ax[0].bar(x,jit,color=['tab:green' if q else 'tab:blue' for q in qualified]);ax[0].axhline(200,color='tab:red',ls='--',label='Whole-PLL requirement: <200 fs')
  for i,y in enumerate(jit):ax[0].text(i,y+7,f'{y:.1f}',ha='center')
  ax[0].set(ylabel='All-on output-chain RMS (fs)',title='Same TT27 fixture, 10 kHz–492 MHz; green: refined candidate');ax[0].legend(loc='lower right')
  ax[1].bar(x,power);ax[1].set(xticks=x,xticklabels=labels,ylabel='Measured chain power (mW)')
  for row in ax:row.grid(axis='y',alpha=.2)
  fig.savefig(out/'all_on_tradeoff.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
