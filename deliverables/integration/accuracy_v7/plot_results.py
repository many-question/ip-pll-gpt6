"""Plot measured solver diagnostics, without presenting them as noise spectra."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H

def main():
    dest = H/'figures'; dest.mkdir(exist_ok=True)
    mesh = json.loads((H/'results/mesh_validation.json').read_text())
    cases = {x['case']: x for x in mesh['cases']}
    fig, ax = plt.subplots(1, 2, figsize=(10.2, 3.8), constrained_layout=True)
    for tag, label in [('1ps','1 ps'), ('halfps','0.5 ps'), ('quarterps','0.25 ps')]:
        key = f'mesh_{tag}_plain'
        if key not in cases: continue
        r = cases[key]
        ax[0].plot(np.array(r['ref_times_s'])*1e9, r['phase_previous_period_rad'], 'o-', label=label)
    ax[0].set(xlabel='Time after common 4 us state (ns)', ylabel='VCO phase at reference edge (rad)', title='Full circuit, observer removed')
    ax[0].legend(); ax[0].grid(alpha=.2)
    for tag,label in [('1ps','1 ps'),('halfps','0.5 ps')]:
        a,b=cases[f'mesh_{tag}_obs'],cases[f'mesh_{tag}_plain']
        dp=np.angle(np.exp(1j*(np.array(b['phase_previous_period_rad'])-a['phase_previous_period_rad'])))
        ax[1].plot(np.array(a['ref_times_s'])*1e9,dp*1e3,'o-',label=label)
    ax[1].set(xlabel='Time after common 4 us state (ns)',ylabel='Phase difference (mrad)',title='Observer absent minus present')
    ax[1].legend(loc='lower left');ax[1].grid(alpha=.2)
    fig.suptitle('TT27, 1.2 V, Q=5, code 6, /4; deterministic numerical diagnostics')
    fig.savefig(dest/'mesh_diagnostics.png',dpi=170);plt.close(fig)
    paths=[(H/'results/settle_1ps_continue_1ps_samples.npz','1 ps'),
           (H/'results/settle_halfps_continue_halfps_samples.npz','0.5 ps')]
    if not all(p.exists() for p,_ in paths):return
    fig,ax=plt.subplots(2,1,figsize=(8.6,5.6),sharex=True,constrained_layout=True)
    for p,label in paths:
        with np.load(p) as z:
            t=z['time']*1e6+4
            ax[0].plot(t,np.unwrap(z['obsphase']),label=label)
            ax[1].plot(t,z['obsctrl'],label=label)
    ax[0].set(ylabel='Sampled VCO phase (rad)',title='Same 1 ps / 4 us physical state, then continued for 4 us')
    ax[1].set(xlabel='Cumulative simulated time (us)',ylabel='Sampled control (V)')
    for a in ax:
        a.axvspan(7,8,color='gray',alpha=.10,label='Evaluation window')
        a.legend(loc='best');a.grid(alpha=.2)
    fig.savefig(dest/'continued_accuracy.png',dpi=170);plt.close(fig)

if __name__=='__main__':main()
