"""Fit deterministic reference-period modulation to consecutive clock edges."""
import numpy as np

def fit_edges(edges,reference_hz=24e6,harmonics=7):
    edges=np.asarray(edges);assert len(edges)>100 and np.all(np.diff(edges)>0)
    midpoint=float(np.mean(edges));x=(edges-midpoint)*1e6
    theta=2*np.pi*reference_hz*(edges-edges[0])
    matrix=np.column_stack([np.ones(len(x)),x,x*x]+[fun(k*theta) for k in range(1,harmonics+1) for fun in [np.cos,np.sin]])
    coef=np.linalg.lstsq(matrix,np.arange(len(edges)),rcond=None)[0]
    frequency=float(coef[1]*1e6);residual=np.arange(len(edges))-matrix@coef
    rows=[]
    for k in range(1,harmonics+1):
        a,b=coef[3+2*(k-1):5+2*(k-1)];beta=float(2*np.pi*np.hypot(a,b))
        phasor=2*np.pi*complex(a,-b)*np.exp(-2j*np.pi*k*reference_hz*edges[0])
        rows.append(dict(harmonic=k,pm_peak_rad=beta,equivalent_deterministic_time_peak_ps=beta/(2*np.pi*frequency)*1e12,
            pm_phasor_absolute_time_rad=[float(phasor.real),float(phasor.imag)],
            pm_phase_absolute_time_rad=float(np.angle(phasor))))
    return dict(carrier_hz=frequency,frequency_drift_hz_per_us=float(2*coef[2]*1e6),
        harmonics=rows,residual_time_rms_ps=float(np.sqrt(np.mean(residual**2))/frequency*1e12),
        edges=len(edges),span_us=float((edges[-1]-edges[0])*1e6),
        note='Consecutive-edge deterministic harmonic fit with quadratic drift. No random-noise source or random-jitter measurement.')

def analytic_control():
    fr=3936e6;fm=24e6;beta=.28;n=np.arange(2000,dtype=float)
    t=n/fr
    for _ in range(8):
        phase=fr*t+beta/(2*np.pi)*np.sin(2*np.pi*fm*t)
        derivative=fr+beta*fm*np.cos(2*np.pi*fm*t)
        t-=(phase-n)/derivative
    result=fit_edges(t)
    error=abs(result['harmonics'][0]['pm_peak_rad']/beta-1)
    phase_error=abs(complex(*result['harmonics'][0]['pm_phasor_absolute_time_rad'])/complex(0,-beta)-1)
    return dict(expected_carrier_hz=fr,expected_pm_peak_rad=beta,
        recovered_carrier_hz=result['carrier_hz'],recovered_pm_peak_rad=result['harmonics'][0]['pm_peak_rad'],
        relative_pm_error=float(error),relative_complex_pm_error=float(phase_error),
        passed=bool(error<1e-8 and phase_error<1e-8 and abs(result['carrier_hz']/fr-1)<1e-10))
