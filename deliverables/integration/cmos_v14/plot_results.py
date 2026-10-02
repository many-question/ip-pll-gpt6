"""Recreate figures from the local immutable Spectre waveform archive."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H, R

rows=json.loads((H/'results/validation.json').read_text())
bycase={x['case']:x for x in rows}

def wave(case):
    row=bycase[case]
    with np.load(R/row['run']/case/'waveforms.npz') as z:
        return dict(z)

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(3,2,figsize=(11,7),sharex=True,sharey=True)
cases=['screen_fb50buf24_a18_ss','screen_fb50buf24_rskew42_a18_ss']
for col,case in enumerate(cases):
    d=wave(case); t=(d['time']-d['time'][-1])*1e9; mask=t>=-2.2
    for row,keys in enumerate([['clk','data'],['XR.qb','XR.ob'],['out']]):
        ax=axs[row,col]
        for key in keys: ax.plot(t[mask],d[key][mask],label=key,lw=1.4)
        ax.axhline(.6,color='gray',ls=':',lw=.7)
        ax.grid(alpha=.18);ax.legend(loc='upper right',ncol=len(keys),fontsize=9)
        ax.set_ylim(-.12,1.38);ax.set_xlim(-2.2,0)
        if col==0:ax.set_ylabel('Voltage (V)')
    axs[0,col].set_title(['Before: output stuck low','After: buffer sizing restores output'][col])
    axs[2,col].set_xlabel('Time relative to end (ns)')
fig.suptitle('Retimer pulse transfer: controlled SS / 60 C comparison\nSame noiseless RF replay and divider; retimer buffers changed',y=.995)
fig.tight_layout(rect=(0,0,1,.93))
fig.savefig(H/'results/retimer_repair.png',dpi=150);plt.close(fig)

fig,axs=plt.subplots(3,1,figsize=(10,7),sharex=True)
d=wave('lc_light_c24_v0p2_i180_ss');t=(d['time']-d['time'][-1])*1e9;mask=t>=-3
axs[0].plot(t[mask],(d['vp']-d['vn'])[mask],label='VCO differential')
axs[1].plot(t[mask],d['clk'][mask],label='RF clock')
axs[1].plot(t[mask],d['q1'][mask],label='Divide by 2',alpha=.8)
axs[2].plot(t[mask],d['data'][mask],label='Divider data',alpha=.8)
axs[2].plot(t[mask],d['out'][mask],label='Retimed output')
for ax in axs:
    ax.legend(loc='upper right',ncol=2);ax.set_ylabel('Voltage (V)');ax.grid(alpha=.18);ax.set_xlim(-3,0)
axs[2].set_xlabel('Time relative to 400 ns (ns)')
fig.suptitle('Actual LC + lighter CMOS chain: SS / 60 C, 1.2 V, Q=5\nIREF=180 uA, code=24, control=0.2 V, 10 fF; fixed control, not locked PLL')
fig.tight_layout(rect=(0,0,1,.92));fig.savefig(H/'results/actual_lc_ss.png',dpi=150);plt.close(fig)

fig,ax=plt.subplots(figsize=(8,4.5))
for family,code,color in [('ssfix',21,'#4667a4'),('light',24,'#d3712b')]:
    pts=[]
    for current in range(100,221,20):
        c=f'lc_{family}_c{code}_v0p2_i{current}_ss'
        if c in bycase:
            w=bycase[c]['wave'];pts.append((current,w['power_mw']['VDD:p'],w['pass_function']))
    ax.plot([p[0] for p in pts],[p[1] for p in pts],color=color,alpha=.6,label=f'{family}: code {code}')
    for x,y,ok in pts:ax.scatter(x,y,color=color,marker='o' if ok else 'x',s=65)
ax.axhline(4,color='black',ls='--',label='Full PLL budget (4 mW)')
ax.set(xlabel='VCO reference bias (uA)',ylabel='Same-VDD test circuit power (mW)',title='Actual LC, SS / 60 C: circles pass; crosses fail timing\nMissing FLL / bias generator / full control still require power')
ax.grid(alpha=.2);ax.legend(fontsize=9);fig.tight_layout()
fig.savefig(H/'results/power_tradeoff.png',dpi=150);plt.close(fig)
print('Wrote three evidence figures')
